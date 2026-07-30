from datetime import date, timedelta
import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.access.permissions import (
    can_generate_schedule,
    can_manage_access_requests,
    can_view_own_schedule,
    can_view_supervisor_schedule,
)
from app.modules.auth_tokens.service import create_temporary_web_token
from app.modules.access_requests.service import (
    approve_access_request,
    get_access_request_report,
    list_pending_access_request_reviews,
    notify_access_request_result,
    reject_access_request,
)
from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.employee_view.service import get_my_schedule
from app.modules.schedule_generation.schema import ScheduleGenerationPreviewCreate
from app.modules.schedule_generation.service import (
    cancel_generation_job,
    confirm_generation_job,
    create_generation_preview,
    generation_job_to_dict,
    get_assignment_for_generation,
    list_generation_options,
    publish_generation_job,
    quick_range_for_assignment,
)
from app.modules.supervisor_view.service import get_supervisor_schedule
from app.modules.users.model import User
from app.modules.users.service import unlink_messenger_account
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
    "تولید برنامه": "GENERATE_SCHEDULE",
    "راهنما": "HELP",
    "منو": "MENU",
    "امروز": "VIEW_DAY_TODAY",
    "فردا": "VIEW_DAY_TOMORROW",
    "پس‌فردا": "VIEW_DAY_AFTER_TOMORROW",
    "ماه جاری": "VIEW_MONTH_CURRENT",
    "ماه بعد": "VIEW_MONTH_NEXT",
    "ماه قبل": "VIEW_MONTH_PREVIOUS",
    "بازگشت": "BACK_MENU",
    "خروج از حساب": "LOGOUT_REQUEST",
    "دسترسی وب مدیریت": "CREATE_WEB_ACCESS",
}

PERSIAN_WEEKDAYS = [
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
    "شنبه",
    "یکشنبه",
]


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


def get_public_base_url() -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    webhook_url = settings.bale_webhook_url.rstrip("/")
    marker = "/bot/"
    if marker in webhook_url:
        return webhook_url.split(marker, 1)[0]
    return ""


def build_help_markup(role: str) -> dict:
    buttons = []
    public_base_url = get_public_base_url()
    if role in {"HR", "ADMIN"} and public_base_url:
        buttons.extend(
            [
                [{"text": "بارگذاری کارکنان و شیفت‌ها", "url": f"{public_base_url}/admin/imports"}],
                [{"text": "فرم وب تولید برنامه", "url": f"{public_base_url}/admin/schedule-generator"}],
                [{"text": "دریافت توکن موقت وب", "callback_data": "CREATE_WEB_ACCESS"}],
            ]
        )
    buttons.append([{"text": "بازگشت", "callback_data": "BACK_MENU"}])
    return {"inline_keyboard": buttons}


def build_web_access_markup() -> dict:
    public_base_url = get_public_base_url()
    buttons = []
    if public_base_url:
        buttons.extend(
            [
                [{"text": "بازکردن صفحه بارگذاری", "url": f"{public_base_url}/admin/imports"}],
                [{"text": "بازکردن تولید برنامه", "url": f"{public_base_url}/admin/schedule-generator"}],
            ]
        )
    buttons.append([{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}])
    return {"inline_keyboard": buttons}


def format_date_button(target_date: date, today: date) -> str:
    if target_date == today:
        label = "امروز"
    elif target_date == today + timedelta(days=1):
        label = "فردا"
    elif target_date == today + timedelta(days=2):
        label = "پس‌فردا"
    else:
        label = PERSIAN_WEEKDAYS[target_date.weekday()]
    return f"{label} · {target_date.strftime('%Y/%m/%d')}"


def build_date_picker_markup(start_date: date | None = None) -> dict:
    today = date.today()
    first_date = start_date or today
    buttons = [
        [
            {
                "text": format_date_button(first_date + timedelta(days=offset), today),
                "callback_data": f"VIEW_DATE:{(first_date + timedelta(days=offset)).isoformat()}",
            }
        ]
        for offset in range(7)
    ]
    buttons.extend(
        [
            [
                {
                    "text": "هفته قبل",
                    "callback_data": f"DATE_WEEK:{(first_date - timedelta(days=7)).isoformat()}",
                },
                {
                    "text": "هفته بعد",
                    "callback_data": f"DATE_WEEK:{(first_date + timedelta(days=7)).isoformat()}",
                },
            ],
            [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
        ]
    )
    return {"inline_keyboard": buttons}


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


def build_supervisor_schedule_markup(target_date: date, show_more_command: str | None = None) -> dict:
    buttons = []
    if show_more_command:
        buttons.append([{"text": "نمایش بیشتر", "callback_data": show_more_command}])
    buttons.extend(
        [
            [
                {
                    "text": "روز قبل",
                    "callback_data": f"VIEW_DATE:{(target_date - timedelta(days=1)).isoformat()}",
                },
                {
                    "text": "روز بعد",
                    "callback_data": f"VIEW_DATE:{(target_date + timedelta(days=1)).isoformat()}",
                },
            ],
            [{"text": "انتخاب تاریخ دیگر", "callback_data": "SELECT_DATE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    )
    return {"inline_keyboard": buttons}


def build_supervisor_full_markup(target_date: date) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "نمایش کمتر",
                    "callback_data": f"SHOW_LESS_SUPERVISOR:{target_date.isoformat()}",
                }
            ],
            [
                {
                    "text": "روز قبل",
                    "callback_data": f"VIEW_DATE:{(target_date - timedelta(days=1)).isoformat()}",
                },
                {
                    "text": "روز بعد",
                    "callback_data": f"VIEW_DATE:{(target_date + timedelta(days=1)).isoformat()}",
                },
            ],
            [{"text": "انتخاب تاریخ دیگر", "callback_data": "SELECT_DATE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    }


def get_help_text(role: str) -> str:
    if role == "SUPERVISOR":
        return "\n".join(
            [
                "راهنمای سرپرست",
                "• افراد روز: برنامه نیروهای تحت سرپرستی در امروز.",
                "• تاریخ: انتخاب یکی از ۷ روز، رفتن به هفته قبل یا بعد و مشاهده برنامه همان روز.",
                "• روز قبل/روز بعد: جابه‌جایی سریع میان برنامه روزها.",
                "• نمایش بیشتر: مشاهده ادامه فهرست نیروها.",
                "• خروج از حساب: قطع اتصال حساب بله پس از تأیید.",
                "سرپرست فقط برنامه نیروهای مجاز خود را مشاهده می‌کند و امکان تغییر یا تولید برنامه ندارد.",
            ]
        )
    if role == "HR":
        return "\n".join(
            [
                "راهنمای منابع انسانی",
                "• برنامه شیفت من و انتخاب ماه: مشاهده برنامه شخصی.",
                "• مشاهده افراد یک روز و انتخاب تاریخ: مشاهده برنامه روزانه نیروها.",
                "• درخواست‌ها: تأیید یا رد درخواست‌های فعال‌سازی.",
                "• عملیات: گزارش درخواست‌ها و سلامت webhook.",
                "• بارگذاری کارکنان و شیفت‌ها: دکمه وب پایین پیام را بزنید؛ /admin/imports فرمان بله نیست.",
                "• تولید برنامه: انتخاب کارمند، الگو و بازه؛ سپس تکمیل فقط برای روزهای خالی، تأیید یا انتشار.",
                "• فرم وب تولید برنامه: دکمه وب پایین پیام را بزنید؛ /admin/schedule-generator فرمان بله نیست.",
                "• برای استفاده از فرم‌ها، ابتدا «دریافت توکن موقت وب» را بزنید و توکن را در فرم وارد کنید.",
                "• خروج از حساب: قطع اتصال حساب بله پس از تأیید.",
            ]
        )
    if role == "ADMIN":
        return "\n".join(
            [
                "راهنمای مدیر سیستم",
                "• برنامه شیفت من، انتخاب ماه، مشاهده افراد و انتخاب تاریخ: مشاهده برنامه‌ها.",
                "• درخواست‌ها: تأیید یا رد فعال‌سازی کاربران.",
                "• عملیات: گزارش درخواست‌ها و لاگ‌های webhook.",
                "• مدیریت داده: با دکمه وب پایین پیام؛ /admin/imports فرمان بله نیست.",
                "• تولید خودکار برنامه: از داخل ربات یا دکمه فرم وب پایین پیام.",
                "• برای استفاده از فرم‌ها، ابتدا «دریافت توکن موقت وب» را بزنید و توکن را در فرم وارد کنید.",
                "• خروج از حساب: قطع اتصال حساب بله پس از تأیید.",
            ]
        )
    return "\n".join(
        [
            "راهنمای کارمند",
            "• برنامه من: خلاصه برنامه شما از ابتدای ماه تا امروز.",
            "• ماه: انتخاب ماه قبل، ماه جاری یا ماه بعد.",
            "• نمایش بیشتر/کمتر: باز یا خلاصه‌کردن جزئیات برنامه.",
            "• بازگشت: برگشتن به منوی اصلی.",
            "• خروج از حساب: قطع اتصال حساب بله پس از تأیید؛ اطلاعات برنامه حذف نمی‌شود.",
        ]
    )


def build_access_requests_markup(requests: list[dict]) -> dict:
    buttons = []
    for access_request in requests:
        request_id = access_request["id"]
        row = []
        if access_request.get("can_approve"):
            row.append(
                {"text": f"تأیید {request_id}", "callback_data": f"APPROVE_ACCESS:{request_id}"}
            )
        row.append({"text": f"رد {request_id}", "callback_data": f"REJECT_ACCESS:{request_id}"})
        buttons.append(row)
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


def build_generation_employee_markup(options: dict) -> dict:
    buttons = [
        [
            {
                "text": f"{employee['personnel_code']} · {employee['full_name']}",
                "callback_data": f"GEN_EMP:{employee['id']}",
            }
        ]
        for employee in options.get("employees", [])
    ]
    buttons.append([{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}])
    return {"inline_keyboard": buttons}


def build_generation_assignment_markup(employee: dict) -> dict:
    buttons = [
        [
            {
                "text": f"{assignment['pattern_name']} · از {assignment['start_date']}",
                "callback_data": f"GEN_ASSIGN:{assignment['id']}",
            }
        ]
        for assignment in employee.get("assignments", [])
    ]
    buttons.extend(
        [
            [{"text": "انتخاب کارمند دیگر", "callback_data": "GENERATE_SCHEDULE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    )
    return {"inline_keyboard": buttons}


def build_generation_range_markup(assignment_id: int) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "۷ روز آینده", "callback_data": f"GEN_RANGE:{assignment_id}:7D"}],
            [{"text": "تا پایان ماه جاری", "callback_data": f"GEN_RANGE:{assignment_id}:CURRENT_MONTH"}],
            [{"text": "ماه بعد", "callback_data": f"GEN_RANGE:{assignment_id}:NEXT_MONTH"}],
            [{"text": "انتخاب الگوی دیگر", "callback_data": "GENERATE_SCHEDULE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    }


def build_generation_preview_markup(job_id: int) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "تأیید و ذخیره پیش‌نویس", "callback_data": f"GEN_CONFIRM:{job_id}"}],
            [{"text": "انتشار برنامه", "callback_data": f"GEN_PUBLISH:{job_id}"}],
            [{"text": "لغو", "callback_data": f"GEN_CANCEL:{job_id}"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    }


def build_generation_confirmed_markup(job_id: int) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "انتشار پیش‌نویس", "callback_data": f"GEN_PUBLISH:{job_id}"}],
            [{"text": "تولید برنامه دیگر", "callback_data": "GENERATE_SCHEDULE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    }


def build_generation_finished_markup() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "تولید برنامه دیگر", "callback_data": "GENERATE_SCHEDULE"}],
            [{"text": "بازگشت به منو", "callback_data": "BACK_MENU"}],
        ]
    }


def build_logout_confirmation_markup() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "تأیید خروج", "callback_data": "LOGOUT_CONFIRM"}],
            [{"text": "انصراف", "callback_data": "LOGOUT_CANCEL"}],
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
        return {
            "type": "welcome",
            "text": "به ربات نمایش شیفت‌های کاری خوش آمدید.\nیکی از گزینه‌های زیر را انتخاب کنید.",
            "reply_markup": build_reply_markup(menu),
        }

    if raw_text in {"MENU", "BACK_MENU"} or normalized in {"منو", "menu", "/menu"}:
        return {"type": "menu", "items": menu, "reply_markup": build_reply_markup(menu)}

    if raw_text == "LOGOUT_REQUEST" or compact in {"خروجازحساب", "خروج", "logout"}:
        return {
            "type": "logout_confirmation",
            "text": "آیا مطمئن هستید که می‌خواهید از حساب خارج شوید؟",
            "reply_markup": build_logout_confirmation_markup(),
        }

    if raw_text == "LOGOUT_CANCEL":
        return {
            "type": "menu",
            "text": "خروج از حساب لغو شد.",
            "items": menu,
            "reply_markup": build_reply_markup(menu),
        }

    if raw_text == "LOGOUT_CONFIRM":
        unlink_messenger_account(db, user)
        return {
            "type": "logged_out",
            "text": "از حساب خارج شدید.\nبرای ورود دوباره، /start را بفرستید.",
            "reply_markup": {"remove_keyboard": True},
        }

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
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        return {
            "type": "date_help",
            "text": "یکی از روزهای زیر را انتخاب کنید.\nبرای روزهای دیگر، هفته را جابه‌جا کنید یا تاریخ را به شکل YYYY-MM-DD بفرستید.",
            "reply_markup": build_date_picker_markup(),
        }

    if raw_text.startswith("DATE_WEEK:"):
        if not can_view_supervisor_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, start_date_text = raw_text.split(":", 1)
        start_date = parse_iso_date(start_date_text)
        return {
            "type": "date_help",
            "text": "یکی از روزهای این هفته را انتخاب کنید.",
            "reply_markup": build_date_picker_markup(start_date),
        }

    if raw_text in {"VIEW_ACCESS_REQUESTS"} or compact in {"درخواستها", "درخواست‌ها"}:
        if not can_manage_access_requests(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        pending_requests = list_pending_access_request_reviews(db, limit=5)
        return {
            "type": "access_requests",
            "data": {"requests": pending_requests},
            "reply_markup": build_access_requests_markup(pending_requests),
        }

    if raw_text in {"VIEW_OPERATIONS"} or compact in {"عملیات"}:
        if not can_manage_access_requests(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        return {
            "type": "operations_menu",
            "text": "بخش عملیات آماده است.",
            "reply_markup": build_operations_markup(),
        }

    if raw_text == "GENERATE_SCHEDULE" or compact in {"تولیدبرنامه"}:
        if not can_generate_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        options = list_generation_options(db)
        return {
            "type": "schedule_generation_employee_select",
            "text": (
                "کارمند موردنظر را انتخاب کنید."
                if options.get("employees")
                else "هیچ کارمند دارای الگوی اختصاص‌یافته پیدا نشد."
            ),
            "data": options,
            "reply_markup": build_generation_employee_markup(options),
        }

    if raw_text.startswith("GEN_EMP:"):
        if not can_generate_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        employee_id = int(raw_text.split(":", 1)[1])
        options = list_generation_options(db)
        employee = next(
            (item for item in options.get("employees", []) if item["id"] == employee_id),
            None,
        )
        if employee is None:
            return {
                "type": "schedule_generation_error",
                "text": "کارمند یا Assignment فعال پیدا نشد.",
                "reply_markup": build_generation_employee_markup(options),
            }
        return {
            "type": "schedule_generation_assignment_select",
            "text": f"الگوی اختصاص‌یافته برای {employee['full_name']} را انتخاب کنید.",
            "data": {"employee": employee},
            "reply_markup": build_generation_assignment_markup(employee),
        }

    if raw_text.startswith("GEN_ASSIGN:"):
        if not can_generate_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        assignment_id = int(raw_text.split(":", 1)[1])
        try:
            assignment = get_assignment_for_generation(db, assignment_id)
        except ValueError:
            return {
                "type": "schedule_generation_error",
                "text": "الگوی اختصاص‌یافته پیدا نشد.",
                "reply_markup": build_generation_finished_markup(),
            }
        return {
            "type": "schedule_generation_range_select",
            "text": "بازه تولید برنامه را انتخاب کنید.",
            "data": {"assignment_id": assignment.id},
            "reply_markup": build_generation_range_markup(assignment.id),
        }

    if raw_text.startswith("GEN_RANGE:"):
        if not can_generate_schedule(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, assignment_id_text, range_key = raw_text.split(":", 2)
        try:
            assignment = get_assignment_for_generation(db, int(assignment_id_text))
            from_date, to_date = quick_range_for_assignment(assignment, range_key)
            job = create_generation_preview(
                db,
                ScheduleGenerationPreviewCreate(
                    employee_id=assignment.employee_id,
                    assignment_id=assignment.id,
                    from_date=from_date,
                    to_date=to_date,
                ),
                get_actor_user_id(user),
            )
        except ValueError as error:
            return {
                "type": "schedule_generation_error",
                "text": f"پیش‌نمایش ایجاد نشد: {error}",
                "reply_markup": build_generation_finished_markup(),
            }
        return {
            "type": "schedule_generation_preview",
            "text": (
                f"پیش‌نمایش #{job.id}\n"
                f"بازه: {job.from_date} تا {job.to_date}\n"
                f"کل روزها: {job.total_days}\n"
                f"روزهای دارای برنامه: {job.total_days - job.missing_days}\n"
                f"روزهای قابل تکمیل: {job.missing_days}\n"
                "یکی از گزینه‌های تأیید، انتشار یا لغو را انتخاب کنید."
            ),
            "data": {"job": generation_job_to_dict(job)},
            "reply_markup": build_generation_preview_markup(job.id),
        }

    generation_actions = {
        "GEN_CONFIRM:": ("confirm", confirm_generation_job),
        "GEN_PUBLISH:": ("publish", publish_generation_job),
        "GEN_CANCEL:": ("cancel", cancel_generation_job),
    }
    for prefix, (action, handler) in generation_actions.items():
        if raw_text.startswith(prefix):
            if not can_generate_schedule(user.role):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
            job_id = int(raw_text.split(":", 1)[1])
            try:
                job = handler(db, job_id, get_actor_user_id(user))
            except ValueError as error:
                return {
                    "type": "schedule_generation_error",
                    "text": f"عملیات انجام نشد: {error}",
                    "reply_markup": build_generation_finished_markup(),
                }
            labels = {
                "confirm": f"پیش‌نویس برنامه تأیید شد. {job.created_schedules} روز ذخیره شد.",
                "publish": f"برنامه منتشر شد. {job.created_schedules} روز ایجاد شده است.",
                "cancel": "تولید برنامه لغو شد و تغییری در برنامه‌ها ایجاد نشد.",
            }
            return {
                "type": "schedule_generation_result",
                "text": labels[action],
                "data": {"job": generation_job_to_dict(job), "action": action},
                "reply_markup": (
                    build_generation_confirmed_markup(job.id)
                    if action == "confirm"
                    else build_generation_finished_markup()
                ),
            }

    if raw_text in {"VIEW_ACCESS_REQUEST_REPORT"}:
        if not can_manage_access_requests(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        report = get_access_request_report(db)
        return {
            "type": "access_request_report",
            "data": report,
            "reply_markup": build_operations_markup(),
        }

    if raw_text in {"VIEW_WEBHOOK_LOG_REPORT"}:
        if not can_manage_access_requests(user.role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        report = get_webhook_log_report(db)
        return {
            "type": "webhook_log_report",
            "data": report,
            "reply_markup": build_operations_markup(),
        }

    if raw_text.startswith("APPROVE_ACCESS:"):
        if not can_manage_access_requests(user.role):
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
        if not can_manage_access_requests(user.role):
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
        return {
            "type": "help",
            "text": get_help_text(user.role),
            "reply_markup": build_help_markup(user.role),
        }

    if raw_text == "CREATE_WEB_ACCESS":
        if user.role not in {"HR", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        _, raw_token = create_temporary_web_token(db, user.id, lifetime_minutes=15)
        return {
            "type": "help",
            "text": "\n".join(
                [
                    "توکن موقت مدیریت وب ایجاد شد.",
                    "اعتبار: ۱۵ دقیقه",
                    "توکن را کپی و در کادر Bearer Token صفحه وب وارد کنید:",
                    raw_token,
                    "این توکن را در اختیار دیگران قرار ندهید.",
                ]
            ),
            "reply_markup": build_web_access_markup(),
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
            "reply_markup": build_supervisor_full_markup(target_date),
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
            "reply_markup": build_supervisor_schedule_markup(target_date, show_more_command),
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
                "reply_markup": build_date_picker_markup(),
            }
        target_date = quick_dates.get(raw_text) or parsed_date or date.today()
        result = get_supervisor_schedule(db, user, target_date)
        show_more_command = f"SHOW_MORE_SUPERVISOR:{target_date.isoformat()}" if len(result.get("employees", [])) > 5 else None
        return {
            "type": "supervisor_schedule",
            "data": result,
            "detail_level": "summary",
            "reply_markup": build_supervisor_schedule_markup(target_date, show_more_command),
        }

    return {
        "type": "help",
        "text": "یکی از گزینه‌ها را انتخاب کنید.",
        "reply_markup": build_back_markup(),
    }
