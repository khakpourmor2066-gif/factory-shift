from datetime import date, timedelta
import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.access.permissions import can_view_own_schedule, can_view_supervisor_schedule
from app.modules.access_requests.service import (
    approve_access_request,
    get_access_request_report,
    list_pending_access_requests,
    notify_access_request_result,
    reject_access_request,
)
from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.employee_view.service import get_my_schedule
from app.modules.supervisor_view.service import get_supervisor_schedule
from app.modules.users.model import User
from app.modules.bot_adapter.services.menu_service import get_menu_for_role
from app.modules.webhook_logs.service import get_webhook_log_report


MENU_COMMANDS = {
    "برنامه من": "VIEW_MY_SHIFT",
    "برنامه شیفت من": "VIEW_MY_SHIFT",
    "افراد روز": "VIEW_DAY_STAFF",
    "مشاهده افراد یک روز": "VIEW_DAY_STAFF",
    "ماه": "SELECT_MONTH",
    "انتخاب ماه": "SELECT_MONTH",
    "تاریخ": "SELECT_DATE",
    "انتخاب تاریخ": "SELECT_DATE",
    "درخواست‌ها": "VIEW_ACCESS_REQUESTS",
    "درخواست ها": "VIEW_ACCESS_REQUESTS",
    "عملیات": "VIEW_OPERATIONS",
    "راهنما": "HELP",
    "منو": "MENU",
    "امروز": "VIEW_DAY_TODAY",
    "فردا": "VIEW_DAY_TOMORROW",
    "پس‌فردا": "VIEW_DAY_AFTER_TOMORROW",
    "ماه جاری": "VIEW_MONTH_CURRENT",
    "ماه بعد": "VIEW_MONTH_NEXT",
    "ماه قبل": "VIEW_MONTH_PREVIOUS",
    "بازگشت": "BACK_MENU",
}


def normalize_digits(text: str) -> str:
    return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def contains_date_pattern(text: str) -> bool:
    return re.search(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b", normalize_digits(text)) is not None


def parse_iso_date(text: str) -> date | None:
    match = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", normalize_digits(text))
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def month_range(month_date: date) -> tuple[date, date]:
    first_day = month_date.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    return first_day, next_month - timedelta(days=1)


def shift_month(month_date: date, months: int) -> date:
    month_index = month_date.year * 12 + month_date.month - 1 + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def build_reply_markup(items: list[str]) -> dict:
    return {
        "inline_keyboard": [
            [{"text": item, "callback_data": MENU_COMMANDS.get(item, item)}]
            for item in items
        ]
    }


def build_back_markup() -> dict:
    return build_reply_markup(["بازگشت"])


def build_summary_markup(show_more_command: str | None = None) -> dict:
    buttons = []
    if show_more_command:
        buttons.append([{"text": "نمایش بیشتر", "callback_data": show_more_command}])
    buttons.append([{"text": "بازگشت", "callback_data": "BACK_MENU"}])
    return {"inline_keyboard": buttons}


def build_full_markup(show_less_command: str = "SHOW_LESS") -> dict:
    return {
        "inline_keyboard": [
            [{"text": "نمایش کمتر", "callback_data": show_less_command}],
            [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
        ]
    }


def build_access_requests_markup(requests: list) -> dict:
    buttons = []
    for access_request in requests:
        request_id = access_request.id
        buttons.append(
            [
                {"text": f"تایید {request_id}", "callback_data": f"APPROVE_ACCESS:{request_id}"},
                {"text": f"رد {request_id}", "callback_data": f"REJECT_ACCESS:{request_id}"},
            ]
        )
    buttons.append([{"text": "بازگشت", "callback_data": "BACK_MENU"}])
    return {"inline_keyboard": buttons}


def build_operations_markup() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "درخواست‌ها", "callback_data": "VIEW_ACCESS_REQUESTS"}],
            [{"text": "گزارش درخواست‌ها", "callback_data": "VIEW_ACCESS_REQUEST_REPORT"}],
            [{"text": "گزارش لاگ‌ها", "callback_data": "VIEW_WEBHOOK_LOG_REPORT"}],
            [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
        ]
    }


def get_actor_user_id(user: User) -> int:
    return int(getattr(user, "id", 0) or 0)


def resolve_user_message(db: Session, user: User, text: str) -> dict:
    menu = get_menu_for_role(user.role)

    raw_text = text.strip()
    normalized = raw_text.lower().replace("ي", "ی").replace("ك", "ک")
    compact = normalized.replace(" ", "")

    if normalized in {"start", "/start"}:
        pending_activation_count = 0
        if db is not None:
            pending_activation_count = len(list_pending_access_requests(db, limit=1000))
        return {
            "type": "welcome",
            "text": "به ربات نمایش شیفت‌های کاری خوش آمدید.\nبرای فعال‌سازی، اگر دکمه «ارسال شماره تلفن» را در پایین صفحه مشاهده می‌کنید، همان را ارسال کنید.\nدر غیر این صورت، ابتدا شماره تلفن همراه را بفرستید.\nمثال:\n0912*******",
            "data": {"pending_activation_count": pending_activation_count},
            "reply_markup": build_reply_markup(menu),
        }

    if raw_text in {"MENU", "BACK_MENU"} or normalized in {"منو", "menu", "/menu"}:
        return {"type": "menu", "items": menu, "reply_markup": build_reply_markup(menu)}

    if raw_text in {"VIEW_MY_SHIFT"} or compact in {"برنامهشیفتمن", "شیفتمن", "برنامهمن"}:
        if not can_view_own_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        today = date.today()
        first_day = today.replace(day=1)
        result = get_my_schedule(db, user, first_day, today)
        show_more_command = f"SHOW_MORE_EMPLOYEE:{first_day.isoformat()}:{today.isoformat()}" if len(result.get("days", [])) > 5 else None
        return {
            "type": "employee_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_summary_markup(show_more_command),
        }

    if raw_text in {"SELECT_MONTH"} or compact in {"انتخابماه", "ماه"}:
        return {
            "type": "month_help",
            "text": "ماه را انتخاب کنید.",
            "reply_markup": build_reply_markup(["ماه قبل", "ماه جاری", "ماه بعد", "بازگشت"]),
        }

    month_offsets = {
        "VIEW_MONTH_PREVIOUS": -1,
        "VIEW_MONTH_CURRENT": 0,
        "VIEW_MONTH_NEXT": 1,
    }
    month_text_offsets = {
        "ماهقبل": -1,
        "ماهگذشته": -1,
        "ماهجاری": 0,
        "ماهفعلی": 0,
        "ماهبعد": 1,
        "ماهبعدی": 1,
    }
    if raw_text in month_offsets or compact in month_text_offsets:
        if not can_view_own_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        offset = month_offsets.get(raw_text, month_text_offsets.get(compact, 0))
        first_day, last_day = month_range(shift_month(date.today(), offset))
        result = get_my_schedule(db, user, first_day, last_day)
        show_more_command = f"SHOW_MORE_EMPLOYEE:{first_day.isoformat()}:{last_day.isoformat()}" if len(result.get("days", [])) > 5 else None
        return {
            "type": "employee_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_summary_markup(show_more_command),
        }

    if raw_text in {"SELECT_DATE"} or compact in {"انتخابتاریخ", "تاریخ"}:
        return {
            "type": "date_help",
            "text": "تاریخ را انتخاب کنید یا YYYY-MM-DD بنویسید.",
            "reply_markup": build_reply_markup(["امروز", "فردا", "پس‌فردا", "بازگشت"]),
        }

    if raw_text in {"VIEW_ACCESS_REQUESTS"} or compact in {"درخواستها", "درخواست‌ها"}:
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        pending_requests = list_pending_access_requests(db, limit=5)
        return {
            "type": "access_requests",
            "data": {"requests": pending_requests},
            "reply_markup": build_access_requests_markup(pending_requests),
        }

    if raw_text in {"VIEW_OPERATIONS"} or compact in {"عملیات"}:
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        return {
            "type": "operations_menu",
            "text": "بخش عملیات آماده است.",
            "reply_markup": build_operations_markup(),
        }

    if raw_text in {"VIEW_ACCESS_REQUEST_REPORT"}:
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        report = get_access_request_report(db)
        return {
            "type": "access_request_report",
            "data": report,
            "reply_markup": build_operations_markup(),
        }

    if raw_text in {"VIEW_WEBHOOK_LOG_REPORT"}:
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        report = get_webhook_log_report(db)
        return {
            "type": "webhook_log_report",
            "data": report,
            "reply_markup": build_operations_markup(),
        }

    if raw_text.startswith("APPROVE_ACCESS:"):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, request_id_text = raw_text.split(":", 1)
        review_status, access_request = approve_access_request(db, int(request_id_text))
        notification_sent = notify_access_request_result(access_request, review_status)
        if access_request is not None:
            create_audit_log(
                db,
                AuditLogCreate(
                    user_id=get_actor_user_id(user),
                    action="access_request_approved_via_bot",
                    before_value="pending",
                    after_value=review_status,
                ),
            )
        return {
            "type": "access_request_review",
            "data": {"action": "approve", "status": review_status, "request": access_request, "notification_sent": notification_sent},
            "reply_markup": build_reply_markup(["درخواست‌ها", "بازگشت"]),
        }

    if raw_text.startswith("REJECT_ACCESS:"):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, request_id_text = raw_text.split(":", 1)
        review_status, access_request = reject_access_request(db, int(request_id_text))
        notification_sent = notify_access_request_result(access_request, review_status)
        if access_request is not None:
            create_audit_log(
                db,
                AuditLogCreate(
                    user_id=get_actor_user_id(user),
                    action="access_request_rejected_via_bot",
                    before_value="pending",
                    after_value=review_status,
                ),
            )
        return {
            "type": "access_request_review",
            "data": {"action": "reject", "status": review_status, "request": access_request, "notification_sent": notification_sent},
            "reply_markup": build_reply_markup(["درخواست‌ها", "بازگشت"]),
        }

    if raw_text in {"HELP"} or compact in {"راهنما", "help", "/help"}:
        if user.role == "SUPERVISOR":
            help_text = "برای مشاهده افراد روز، «افراد روز» را بزنید."
        else:
            help_text = "برای دیدن برنامه خود، «برنامه من» را بزنید."
        return {
            "type": "help",
            "text": help_text,
            "reply_markup": build_back_markup(),
        }

    if raw_text.startswith("SHOW_MORE_EMPLOYEE:"):
        if not can_view_own_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, from_text, to_text = raw_text.split(":", 2)
        result = get_my_schedule(db, user, parse_iso_date(from_text) or date.today(), parse_iso_date(to_text) or date.today())
        return {
            "type": "employee_schedule",
            "data": result,
            "detail_level": "full",
            "reply_markup": build_full_markup(f"SHOW_LESS_EMPLOYEE:{from_text}:{to_text}"),
        }

    if raw_text.startswith("SHOW_LESS_EMPLOYEE:"):
        if not can_view_own_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, from_text, to_text = raw_text.split(":", 2)
        from_date = parse_iso_date(from_text) or date.today()
        to_date = parse_iso_date(to_text) or date.today()
        result = get_my_schedule(db, user, from_date, to_date)
        show_more_command = f"SHOW_MORE_EMPLOYEE:{from_date.isoformat()}:{to_date.isoformat()}" if len(result.get("days", [])) > 5 else None
        return {
            "type": "employee_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_summary_markup(show_more_command),
        }

    if raw_text.startswith("SHOW_MORE_SUPERVISOR:"):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, date_text = raw_text.split(":", 1)
        target_date = parse_iso_date(date_text) or date.today()
        result = get_supervisor_schedule(db, user, target_date)
        return {
            "type": "supervisor_schedule",
            "data": result,
            "detail_level": "full",
            "reply_markup": build_full_markup(f"SHOW_LESS_SUPERVISOR:{date_text}"),
        }

    if raw_text.startswith("SHOW_LESS_SUPERVISOR:"):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, date_text = raw_text.split(":", 1)
        target_date = parse_iso_date(date_text) or date.today()
        result = get_supervisor_schedule(db, user, target_date)
        show_more_command = f"SHOW_MORE_SUPERVISOR:{target_date.isoformat()}" if len(result.get("employees", [])) > 5 else None
        return {
            "type": "supervisor_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_summary_markup(show_more_command),
        }

    quick_dates = {
        "VIEW_DAY_STAFF": date.today(),
        "VIEW_DAY_TODAY": date.today(),
        "VIEW_DAY_TOMORROW": date.today() + timedelta(days=1),
        "VIEW_DAY_AFTER_TOMORROW": date.today() + timedelta(days=2),
    }
    if (
        raw_text in quick_dates
        or ("افراد" in normalized and "روز" in normalized)
        or normalized.startswith("انتخاب تاریخ")
        or contains_date_pattern(normalized)
    ):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        parsed_date = parse_iso_date(normalized)
        if parsed_date is None and contains_date_pattern(normalized):
            return {
                "type": "date_help",
                "text": "تاریخ معتبر نیست. نمونه درست: 2026-07-26",
                "reply_markup": build_reply_markup(["امروز", "فردا", "پس‌فردا", "بازگشت"]),
            }
        target_date = quick_dates.get(raw_text) or parsed_date or date.today()
        result = get_supervisor_schedule(db, user, target_date)
        show_more_command = f"SHOW_MORE_SUPERVISOR:{target_date.isoformat()}" if len(result.get("employees", [])) > 5 else None
        return {
            "type": "supervisor_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_summary_markup(show_more_command),
        }

    return {
        "type": "help",
        "text": "یکی از گزینه‌ها را انتخاب کنید.",
        "reply_markup": build_back_markup(),
    }
