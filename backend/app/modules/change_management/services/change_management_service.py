from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.change_management.model import AuditLog, Notification, ScheduleException
from app.modules.change_management.schemas.change_management import (
    AuditLogCreate,
    NotificationCreate,
    ScheduleExceptionCreate,
)


def create_schedule_exception(db: Session, payload: ScheduleExceptionCreate) -> ScheduleException:
    exception = ScheduleException(**payload.model_dump())
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return exception


def create_notification(db: Session, payload: NotificationCreate) -> Notification:
    notification = Notification(user_id=payload.user_id, message=payload.message, sent_status=True)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_notification_read(db: Session, notification_id: int) -> Notification | None:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        return None
    notification.read_status = True
    notification.read_time = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


def create_audit_log(db: Session, payload: AuditLogCreate) -> AuditLog:
    audit_log = AuditLog(**payload.model_dump())
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def list_audit_logs(db: Session, limit: int = 20) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()


def get_audit_log_report(db: Session, limit: int = 5) -> dict:
    rows = db.query(AuditLog).all()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.action] = counts.get(row.action, 0) + 1
    latest = sorted(rows, key=lambda row: row.id, reverse=True)[:limit]
    return {
        "total": len(rows),
        "counts": counts,
        "latest": latest,
    }


def list_notifications(db: Session, user_id: int) -> list[Notification]:
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.id.desc()).all()
