from sqlalchemy.orm import Session

from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.access_requests.model import AccessRequest
from app.modules.bot_adapter.bale import BaleAdapter
from app.modules.employees.model import Employee
from app.modules.users.model import User


def normalize_mobile(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits.startswith("98") and len(digits) == 12:
        return "0" + digits[2:]
    return digits


def format_contact_text(phone_number: str) -> str:
    return f"CONTACT_MOBILE:{normalize_mobile(phone_number)}"


def extract_contact_mobile(text: str | None) -> str | None:
    if not text or not text.startswith("CONTACT_MOBILE:"):
        return None
    mobile = normalize_mobile(text.split(":", 1)[1])
    return mobile if mobile else None


def combine_pending_contact_with_code(db: Session, *, platform: str, messenger_user_id: str, text: str) -> str:
    pending_request = (
        db.query(AccessRequest)
        .filter(AccessRequest.platform == platform)
        .filter(AccessRequest.messenger_user_id == messenger_user_id)
        .filter(AccessRequest.status == "pending")
        .first()
    )
    mobile = extract_contact_mobile(pending_request.latest_text if pending_request else None)
    if not mobile:
        return text
    return f"ثبت {mobile} {text}"


def get_or_create_access_request(
    db: Session,
    *,
    platform: str,
    messenger_user_id: str,
    latest_text: str | None,
) -> AccessRequest:
    access_request = (
        db.query(AccessRequest)
        .filter(AccessRequest.platform == platform)
        .filter(AccessRequest.messenger_user_id == messenger_user_id)
        .filter(AccessRequest.status == "pending")
        .first()
    )
    if access_request is None:
        access_request = AccessRequest(
            platform=platform,
            messenger_user_id=messenger_user_id,
            latest_text=latest_text,
            status="pending",
            request_count=1,
        )
        db.add(access_request)
    else:
        access_request.latest_text = latest_text
        access_request.request_count = (access_request.request_count or 0) + 1
    db.commit()
    db.refresh(access_request)
    return access_request


def update_access_request_status(db: Session, access_request: AccessRequest, status: str) -> AccessRequest:
    access_request.status = status
    db.commit()
    db.refresh(access_request)
    return access_request


def list_pending_access_requests(db: Session, limit: int = 5) -> list[AccessRequest]:
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.status == "pending")
        .order_by(AccessRequest.created_at.desc())
        .limit(limit)
        .all()
    )


def get_access_request(db: Session, request_id: int) -> AccessRequest | None:
    return db.query(AccessRequest).filter(AccessRequest.id == request_id).first()


def approve_access_request(db: Session, request_id: int) -> tuple[str, AccessRequest | None]:
    access_request = get_access_request(db, request_id)
    if access_request is None:
        return "not_found", None
    if access_request.status != "pending":
        return "already_reviewed", access_request

    approved, approval_status, _ = activate_access_by_hr_identity(
        db,
        platform=access_request.platform,
        messenger_user_id=access_request.messenger_user_id,
        text=access_request.latest_text or "",
    )
    if approved:
        refreshed_request = get_access_request(db, request_id)
        return "approved", refreshed_request
    if approval_status in {"identity_missing", "identity_not_matched", "messenger_already_linked"}:
        return approval_status, access_request
    return "not_approved", access_request


def reject_access_request(db: Session, request_id: int) -> tuple[str, AccessRequest | None]:
    access_request = get_access_request(db, request_id)
    if access_request is None:
        return "not_found", None
    if access_request.status != "pending":
        return "already_reviewed", access_request
    return "rejected", update_access_request_status(db, access_request, "rejected")


def notify_access_request_result(access_request: AccessRequest | None, review_status: str) -> bool:
    if access_request is None or access_request.platform != "bale":
        return False
    messages = {
        "approved": "درخواست دسترسی شما تایید شد. برای شروع /start را بفرستید.",
        "rejected": "درخواست دسترسی شما رد شد. برای پیگیری با مدیر سیستم تماس بگیرید.",
    }
    message = messages.get(review_status)
    if not message:
        return False
    try:
        BaleAdapter().send_message(access_request.messenger_user_id, message)
        return True
    except Exception:
        return False


def get_access_request_report(db: Session) -> dict:
    rows = db.query(AccessRequest).all()
    counts = {"pending": 0, "approved": 0, "rejected": 0, "other": 0}
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
        else:
            counts["other"] += 1
    latest = sorted(rows, key=lambda row: row.created_at, reverse=True)[:5]
    return {
        "counts": counts,
        "total": len(rows),
        "latest": latest,
    }


def format_access_request_message(messenger_user_id: str, request_id: int | None = None) -> str:
    lines = [
        "حساب شما هنوز فعال نشده است.",
        f"شناسه بله شما: {messenger_user_id}",
    ]
    if request_id is not None:
        lines.append(f"شماره درخواست دسترسی: {request_id}")
    lines.extend(
        [
            "این درخواست ثبت شد و باید توسط مدیر سیستم تأیید شود.",
            "اگر اطلاعات شما در سامانه ثبت شده، این شناسه را برای مدیر ارسال کنید.",
        ]
    )
    return "\n".join(lines)


def parse_identity_text(text: str) -> tuple[str, str] | None:
    normalized_text = text.replace("ثبت", " ").replace("کد", " ")
    parts = [part.strip() for part in normalized_text.replace("\n", " ").split() if part.strip()]
    mobile = None
    personnel_code = None
    for part in parts:
        normalized_mobile = normalize_mobile(part)
        if mobile is None and normalized_mobile.startswith("09") and len(normalized_mobile) == 11:
            mobile = normalized_mobile
            continue
        if personnel_code is None and any(ch.isdigit() for ch in part) and not normalized_mobile.startswith("09"):
            personnel_code = part.strip()
    if mobile and personnel_code:
        return mobile, personnel_code
    return None


def activate_access_by_hr_identity(
    db: Session,
    *,
    platform: str,
    messenger_user_id: str,
    text: str,
) -> tuple[bool, str, int | None]:
    identity = parse_identity_text(text)
    if identity is None:
        return False, "identity_missing", None

    mobile, personnel_code = identity
    employee = (
        db.query(Employee)
        .filter(Employee.mobile == mobile)
        .filter(Employee.personnel_code == personnel_code)
        .filter(Employee.is_active.is_(True))
        .first()
    )
    if employee is None:
        return False, "identity_not_matched", None

    existing_user = db.query(User).filter(User.messenger_user_id == messenger_user_id).first()
    if existing_user is not None and existing_user.id != employee.user_id:
        return False, "messenger_already_linked", None

    user = db.query(User).filter(User.id == employee.user_id).first() if employee.user_id else None
    if user is None:
        user = User(mobile=mobile, role="EMPLOYEE", messenger_user_id=messenger_user_id, is_active=True)
        db.add(user)
        db.flush()
        employee.user_id = user.id
    else:
        user.mobile = mobile
        user.messenger_user_id = messenger_user_id
        user.is_active = True

    access_request = get_or_create_access_request(
        db,
        platform=platform,
        messenger_user_id=messenger_user_id,
        latest_text=text,
    )
    access_request.status = "approved"
    db.commit()
    db.refresh(access_request)
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=user.id,
            action="hr_identity_activated",
            before_value="pending",
            after_value="approved",
        ),
    )
    return True, "approved", access_request.id


def format_identity_request_message(messenger_user_id: str, request_id: int | None = None) -> str:
    lines = [
        "برای فعال‌سازی، ابتدا شماره تلفن همراه را بفرستید.",
        "اگر دکمه ارسال شماره را می‌بینید، همان را ارسال کنید.",
        "بعد از دریافت شماره، کد کارمندی را جداگانه بفرستید.",
        "نمونه مرحله دوم: EMP-001",
        f"شناسه بله شما: {messenger_user_id}",
    ]
    if request_id is not None:
        lines.append(f"شماره درخواست دسترسی: {request_id}")
    return "\n".join(lines)


def format_identity_not_matched_message(messenger_user_id: str, request_id: int | None = None) -> str:
    lines = [
        "اطلاعات ارسالی با لیست منابع انسانی تطابق نداشت.",
        "شماره موبایل و کد کارمندی را دوباره بررسی کنید.",
        "نمونه: ثبت 09120000002 EMP-001",
        f"شناسه بله شما: {messenger_user_id}",
    ]
    if request_id is not None:
        lines.append(f"شماره درخواست دسترسی: {request_id}")
    return "\n".join(lines)


def format_access_approved_message() -> str:
    return "دسترسی شما فعال شد. برای شروع /start را بفرستید."


def format_contact_received_message(messenger_user_id: str, request_id: int | None = None) -> str:
    lines = [
        "شماره تلفن دریافت شد.",
        "اکنون فقط کد کارمندی را بفرستید.",
        "نمونه: EMP-001",
        f"شناسه بله شما: {messenger_user_id}",
    ]
    if request_id is not None:
        lines.append(f"شماره درخواست دسترسی: {request_id}")
    return "\n".join(lines)
