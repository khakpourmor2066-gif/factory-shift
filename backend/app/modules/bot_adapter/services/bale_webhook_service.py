from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.access_requests.service import (
    activate_access_by_hr_identity,
    combine_pending_contact_with_code,
    format_access_approved_message,
    format_contact_received_message,
    format_contact_text,
    format_identity_not_matched_message,
    format_identity_request_message,
    extract_contact_mobile,
    get_or_create_access_request,
)
from app.modules.bot_adapter.bale import BaleAdapter
from app.modules.bot_adapter.handlers.bot_handler import resolve_user_message
from app.modules.bot_adapter.services.webhook_service import format_bot_response
from app.modules.users.model import User
from app.modules.webhook_logs.service import create_webhook_log


def extract_bale_incoming_message(payload: dict) -> tuple[str, str]:
    callback_query = payload.get("callback_query") or {}
    if isinstance(callback_query, dict) and callback_query:
        data = callback_query.get("data") or callback_query.get("callback_data")
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        sender = callback_query.get("from") or {}
        messenger_user_id = (
            str(chat.get("id"))
            if chat.get("id") is not None
            else str(sender.get("id"))
        )
        if not messenger_user_id or not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid bale callback payload")
        return messenger_user_id, str(data)

    message = payload.get("message") or payload.get("edited_message") or {}
    if not isinstance(message, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid bale webhook payload")

    contact = message.get("contact") or {}
    phone_number = contact.get("phone_number") if isinstance(contact, dict) else None
    text = message.get("text")
    if not text and phone_number:
        text = format_contact_text(str(phone_number))
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message text is required")

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    messenger_user_id = (
        str(chat.get("id"))
        if chat.get("id") is not None
        else str(sender.get("id"))
    )

    if not messenger_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message sender is required")

    return messenger_user_id, text


def try_send_bale_message(bot_adapter: BaleAdapter, messenger_user_id: str, text: str, reply_markup: dict | None = None) -> bool:
    if not (settings.bale_bot_token or settings.bale_send_url):
        return False
    try:
        bot_adapter.send_message(messenger_user_id, text, reply_markup)
        return True
    except Exception:
        return False


def build_contact_request_markup() -> dict:
    return {
        "keyboard": [[{"text": "ارسال شماره تلفن", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def resolve_bale_webhook_message(db: Session, payload: dict) -> dict:
    messenger_user_id, text = extract_bale_incoming_message(payload)
    bot_adapter = BaleAdapter()
    user = (
        db.query(User)
        .filter(User.messenger_user_id == messenger_user_id)
        .filter(User.is_active.is_(True))
        .first()
    )
    if user is None:
        contact_mobile = extract_contact_mobile(text)
        if contact_mobile:
            create_webhook_log(
                db,
                platform="bale",
                messenger_user_id=messenger_user_id,
                direction="incoming",
                event_type="contact_received",
                request_text=text,
            )
            access_request = get_or_create_access_request(
                db,
                platform="bale",
                messenger_user_id=messenger_user_id,
                latest_text=text,
            )
            message_sent = try_send_bale_message(
                bot_adapter,
                messenger_user_id,
                format_contact_received_message(messenger_user_id, access_request.id),
                )
            create_webhook_log(
                db,
                platform="bale",
                messenger_user_id=messenger_user_id,
                direction="outgoing",
                event_type="contact_received",
                request_text=text,
                response_status="contact_received",
                response_text="شماره تلفن دریافت شد.",
                sent_status=message_sent,
            )
            return {
                "ok": True,
                "status": "contact_received",
                "messenger_user_id": messenger_user_id,
                "access_request_id": access_request.id,
                "message_sent": message_sent,
            }

        activation_text = combine_pending_contact_with_code(
            db,
            platform="bale",
            messenger_user_id=messenger_user_id,
            text=text,
        )
        approved, approval_status, access_request_id = activate_access_by_hr_identity(
            db,
            platform="bale",
            messenger_user_id=messenger_user_id,
            text=activation_text,
        )
        if approved:
            message_sent = try_send_bale_message(
                bot_adapter,
                messenger_user_id,
                format_access_approved_message(),
            )
            create_webhook_log(
                db,
                platform="bale",
                messenger_user_id=messenger_user_id,
                direction="outgoing",
                event_type="access_approved",
                request_text=activation_text,
                response_status="access_approved",
                response_text="دسترسی شما فعال شد.",
                sent_status=message_sent,
            )
            return {
                "ok": True,
                "status": "access_approved",
                "messenger_user_id": messenger_user_id,
                "access_request_id": access_request_id,
                "message_sent": message_sent,
            }

        access_request = get_or_create_access_request(
            db,
            platform="bale",
            messenger_user_id=messenger_user_id,
            latest_text=activation_text,
        )
        if approval_status == "identity_not_matched":
            response_text = format_identity_not_matched_message(messenger_user_id, access_request.id)
        else:
            response_text = format_identity_request_message(messenger_user_id, access_request.id)
        message_sent = try_send_bale_message(
            bot_adapter,
            messenger_user_id,
            response_text,
            build_contact_request_markup() if approval_status == "identity_missing" else None,
        )
        create_webhook_log(
            db,
            platform="bale",
            messenger_user_id=messenger_user_id,
            direction="outgoing",
            event_type="unknown_user",
            request_text=activation_text,
            response_status=approval_status,
            response_text=response_text,
            sent_status=message_sent,
        )
        return {
            "ok": True,
            "status": "unknown_user",
            "messenger_user_id": messenger_user_id,
            "access_request_id": access_request.id,
            "approval_status": approval_status,
            "message_sent": message_sent,
        }

    response = resolve_user_message(db, user, text)
    message_sent = try_send_bale_message(
        bot_adapter,
        messenger_user_id,
        format_bot_response(response),
        response.get("reply_markup"),
    )
    create_webhook_log(
        db,
        platform="bale",
        messenger_user_id=messenger_user_id,
        direction="outgoing",
        event_type=response.get("type", "handled"),
        request_text=text,
        response_status=response.get("type", "handled"),
        response_text=format_bot_response(response),
        sent_status=message_sent,
    )
    return {
        "ok": True,
        "status": "handled",
        "messenger_user_id": messenger_user_id,
        "message_sent": message_sent,
        "response": response,
    }
