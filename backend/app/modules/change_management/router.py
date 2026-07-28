from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.change_management.schemas.change_management import (
    AuditLogCreate,
    AuditLogRead,
    NotificationCreate,
    NotificationRead,
    ScheduleExceptionCreate,
    ScheduleExceptionRead,
)
from app.modules.change_management.services.change_management_service import (
    create_audit_log,
    create_notification,
    create_schedule_exception,
    get_audit_log_report,
    list_audit_logs,
    list_notifications,
    mark_notification_read,
)

router = APIRouter(prefix="/change-management", tags=["change-management"])


@router.post("/exceptions", response_model=ScheduleExceptionRead)
def create_exception_endpoint(payload: ScheduleExceptionCreate, db: Session = Depends(get_db)):
    return create_schedule_exception(db, payload)


@router.post("/notifications", response_model=NotificationRead)
def create_notification_endpoint(payload: NotificationCreate, db: Session = Depends(get_db)):
    return create_notification(db, payload)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read_endpoint(notification_id: int, db: Session = Depends(get_db)):
    notification = mark_notification_read(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return notification


@router.get("/notifications/{user_id}", response_model=list[NotificationRead])
def list_notifications_endpoint(user_id: int, db: Session = Depends(get_db)):
    return list_notifications(db, user_id)


@router.post("/audit", response_model=AuditLogRead)
def create_audit_endpoint(payload: AuditLogCreate, db: Session = Depends(get_db)):
    return create_audit_log(db, payload)


@router.get("/audit", response_model=list[AuditLogRead])
def list_audit_endpoint(limit: int = 20, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 100))
    return list_audit_logs(db, safe_limit)


@router.get("/audit/report")
def audit_report_endpoint(db: Session = Depends(get_db)):
    return get_audit_log_report(db)
