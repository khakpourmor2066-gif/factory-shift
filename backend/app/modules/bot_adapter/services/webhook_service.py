from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.bot_adapter.base import BotAdapter
from app.modules.bot_adapter.bale import BaleAdapter
from app.modules.bot_adapter.handlers.bot_handler import resolve_user_message
from app.modules.bot_adapter.rubika import RubikaAdapter
from app.modules.bot_adapter.schemas.messages import BotWebhookPayload
from app.modules.users.model import User


def get_platform_adapter(platform: str) -> BotAdapter:
    normalized = platform.strip().lower()
    if normalized == "rubika":
        return RubikaAdapter()
    return BaleAdapter()


def format_shift_status(status: str | None) -> str:
    labels = {
        "DAY": "روز",
        "NIGHT": "شب",
        "REST": "استراحت",
        "OFF": "استراحت",
        "WORK": "کار",
    }
    if not status:
        return "-"
    normalized = str(status).strip().upper()
    return labels.get(normalized, str(status))


def summarize_shift_statuses(items: list[dict]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        label = format_shift_status(item.get("status"))
        counts[label] = counts.get(label, 0) + 1
    preferred_order = ["روز", "شب", "استراحت", "کار"]
    ordered_labels = [label for label in preferred_order if label in counts]
    ordered_labels.extend(label for label in counts if label not in ordered_labels)
    return " · ".join(f"{label}: {counts[label]}" for label in ordered_labels)


def format_bot_response(response: dict) -> str:
    response_type = response.get("type", "menu")
    detail_level = response.get("detail_level", "summary")
    if response_type == "access_requests":
        requests = response.get("data", {}).get("requests", [])
        if not requests:
            return "درخواست در انتظار وجود ندارد.\nبرای گزارش کلی از منوی «عملیات» استفاده کنید."
        lines = [
            f"درخواست‌های در انتظار: {len(requests)}",
            "برای بررسی، دکمه تایید یا رد همان درخواست را بزنید.",
        ]
        for access_request in requests:
            lines.append(
                f"#{access_request.id} · {access_request.messenger_user_id} · تعداد: {access_request.request_count}"
            )
        return "\n".join(lines)
    if response_type == "access_request_review":
        data = response.get("data", {})
        review_status = data.get("status")
        access_request = data.get("request")
        request_label = f"#{access_request.id}" if access_request is not None else ""
        messages = {
            "approved": f"درخواست {request_label} تایید و کاربر فعال شد.",
            "rejected": f"درخواست {request_label} رد شد.",
            "identity_missing": f"درخواست {request_label} اطلاعات موبایل و کد کارمندی ندارد.",
            "identity_not_matched": f"درخواست {request_label} با لیست منابع انسانی تطابق ندارد.",
            "messenger_already_linked": f"درخواست {request_label} به شناسه بله دیگری متصل است.",
            "already_reviewed": f"درخواست {request_label} قبلاً بررسی شده است.",
            "not_found": "درخواست پیدا نشد.",
        }
        return messages.get(review_status, "بررسی درخواست انجام نشد.")
    if response_type == "identity_missing":
        return "\n".join(
            [
                "برای فعال‌سازی، ابتدا شماره تلفن همراه را بفرستید.",
                "بعد از دریافت شماره، کد کارمندی را جداگانه بفرستید.",
                "نمونه مرحله دوم: EMP-001",
            ]
        )
    if response_type == "contact_received":
        data = response.get("data", {})
        contact_mobile = data.get("contact_mobile")
        lines = ["شماره تلفن همراه دریافت شد."]
        if contact_mobile:
            lines.append(f"شماره: {contact_mobile}")
        lines.extend(["اکنون، شماره کارمندی خود را ارسال کنید.", "مثال: EMP-001"])
        return "\n".join(lines)
    if response_type == "operations_menu":
        return "\n".join(
            [
                response.get("text", "بخش عملیات آماده است."),
                "گزینه موردنظر را انتخاب کنید:",
                "درخواست‌ها: بررسی تایید/رد",
                "گزارش درخواست‌ها: وضعیت درخواست‌های دسترسی",
                "گزارش لاگ‌ها: وضعیت webhook و ارسال پیام",
            ]
        )
    if response_type == "access_request_report":
        report = response.get("data", {})
        counts = report.get("counts", {})
        return "\n".join(
            [
                "گزارش درخواست‌های دسترسی",
                f"کل درخواست‌ها: {report.get('total', 0)}",
                f"در انتظار: {counts.get('pending', 0)}",
                f"تایید شده: {counts.get('approved', 0)}",
                f"رد شده: {counts.get('rejected', 0)}",
            ]
        )
    if response_type == "webhook_log_report":
        report = response.get("data", {})
        counts = report.get("counts", {})
        return "\n".join(
            [
                "گزارش لاگ‌های webhook",
                f"کل لاگ‌ها: {report.get('total', 0)}",
                f"ورودی: {counts.get('incoming', 0)}",
                f"خروجی: {counts.get('outgoing', 0)}",
                f"ارسال موفق: {counts.get('sent', 0)}",
                f"ارسال ناموفق: {counts.get('failed', 0)}",
            ]
        )
    if response_type in {"logout_confirmation", "logged_out"}:
        return response.get("text", "")
    if response_type.startswith("schedule_generation_"):
        return response.get("text", "")
    if response_type == "employee_schedule":
        data = response.get("data", {})
        days = data.get("days", [])
        if not days:
            return "برای این بازه برنامه‌ای ثبت نشده است.\nاز «ماه» بازه دیگری را انتخاب کنید."
        lines = [
            f"{data.get('employee_name', 'شما')} · {len(days)} روز",
            f"خلاصه: {summarize_shift_statuses(days)}",
        ]
        visible_days = days if detail_level == "full" else days[:5]
        if detail_level == "full":
            lines.append("جزئیات:")
        for day in visible_days:
            lines.append(f"{day.get('date')}: {format_shift_status(day.get('status'))}")
        if detail_level != "full" and len(days) > 5:
            lines.append(f"+ {len(days) - 5} روز دیگر")
        return "\n".join(lines)
    if response_type == "supervisor_schedule":
        data = response.get("data", {})
        employees = data.get("employees", [])
        target_date = data.get("date", "")
        if not employees:
            return f"برای {target_date} برنامه‌ای ثبت نشده است.\nاز «تاریخ» روز دیگری را انتخاب کنید."
        lines = [
            f"{target_date} · {len(employees)} نفر",
            f"خلاصه: {summarize_shift_statuses(employees)}",
        ]
        visible_employees = employees if detail_level == "full" else employees[:5]
        if detail_level == "full":
            lines.append("جزئیات:")
        for employee in visible_employees:
            lines.append(f"{employee.get('full_name')}: {format_shift_status(employee.get('status'))}")
        if detail_level != "full" and len(employees) > 5:
            lines.append(f"+ {len(employees) - 5} نفر دیگر")
        return "\n".join(lines)
    if response_type == "date_help":
        return response.get("text", "تاریخ را انتخاب کنید یا YYYY-MM-DD بنویسید.")
    if response_type == "month_help":
        return response.get("text", "ماه را انتخاب کنید.")
    if response_type == "help":
        return response.get("text", "دکمه‌ها را بزنید یا YYYY-MM-DD بنویسید.")
    if response_type == "unknown":
        return response.get("text", "یک دکمه را انتخاب کنید.")
    if response_type == "welcome":
        text = response.get("text", "خوش آمدید.")
        data = response.get("data", {})
        pending_activation_count = data.get("pending_activation_count")
        lines = [text]
        if pending_activation_count is not None:
            lines.append(f"تعداد درخواست‌های فعال‌سازی بررسی‌نشده: {pending_activation_count}")
        return "\n".join(lines)
    if response_type == "menu":
        return response.get("text", "منو")
    items = response.get("items", [])
    return " | ".join(items) if items else "منو آماده است"


def resolve_webhook_message(db: Session, payload: BotWebhookPayload) -> dict:
    user = (
        db.query(User)
        .filter(User.messenger_user_id == payload.messenger_user_id)
        .filter(User.is_active.is_(True))
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active messenger user not found")

    platform = payload.platform or settings.default_bot_platform
    response = resolve_user_message(db, user, payload.text)
    bot_adapter = get_platform_adapter(platform)
    bot_text = format_bot_response(response)
    try:
        bot_adapter.send_message(payload.messenger_user_id, bot_text, response.get("reply_markup"))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="messaging platform delivery failed",
        ) from exc
    return {
        "ok": True,
        "platform": platform,
        "messenger_user_id": payload.messenger_user_id,
        "response": response,
    }
