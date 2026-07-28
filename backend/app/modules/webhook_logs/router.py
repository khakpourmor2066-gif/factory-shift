from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.users.model import User
from app.modules.webhook_logs.schema import WebhookLogReport
from app.modules.webhook_logs.service import get_webhook_log_report

router = APIRouter(prefix="/webhook-logs", tags=["webhook-logs"])


@router.get("/report", response_model=WebhookLogReport)
def webhook_log_report_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return get_webhook_log_report(db)
