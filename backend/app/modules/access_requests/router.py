from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.access_requests.model import AccessRequest
from app.modules.access_requests.schema import AccessRequestRead, AccessRequestReport
from app.modules.access_requests.service import (
    approve_access_request,
    get_access_request_report,
    notify_access_request_result,
    reject_access_request,
)
from app.modules.users.model import User

router = APIRouter(prefix="/access-requests", tags=["access-requests"])


@router.get("/report", response_model=AccessRequestReport)
def access_request_report_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"ADMIN", "HR"})
    return get_access_request_report(db)


@router.get("/pending", response_model=list[AccessRequestRead])
def list_pending_access_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"ADMIN", "HR"})
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.status == "pending")
        .order_by(AccessRequest.created_at.desc())
        .all()
    )


@router.patch("/{request_id}/status", response_model=AccessRequestRead)
def update_access_request_status_endpoint(
    request_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"ADMIN", "HR"})
    access_request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if access_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="access request not found")
    status_value = str(payload.get("status", "")).strip().lower()
    if status_value not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")
    before_status = access_request.status
    if status_value == "approved":
        review_status, updated_request = approve_access_request(db, request_id)
        if review_status != "approved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=review_status)
    else:
        review_status, updated_request = reject_access_request(db, request_id)
        if review_status != "rejected":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=review_status)
    notify_access_request_result(updated_request, review_status)
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=current_user.id,
            action="access_request_status_updated",
            before_value=before_status,
            after_value=review_status,
        ),
    )
    return updated_request
