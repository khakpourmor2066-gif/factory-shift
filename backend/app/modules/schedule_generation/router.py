from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.schedule_generation.schema import ScheduleGenerationPreviewCreate
from app.modules.schedule_generation.service import (
    cancel_generation_job,
    confirm_generation_job,
    create_generation_preview,
    generation_job_to_dict,
    get_generation_job,
    list_generation_options,
    publish_generation_job,
)
from app.modules.users.model import User


router = APIRouter(prefix="/schedule-generation", tags=["schedule-generation"])


def require_generation_role(user: User) -> None:
    require_roles(user, {"HR", "ADMIN"})


@router.get("/options")
def generation_options_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    return list_generation_options(db)


@router.post("/preview")
def generation_preview_endpoint(
    payload: ScheduleGenerationPreviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    try:
        return generation_job_to_dict(create_generation_preview(db, payload, current_user.id))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{job_id}")
def generation_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    try:
        return generation_job_to_dict(get_generation_job(db, job_id))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{job_id}/confirm")
def generation_confirm_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    return _transition(confirm_generation_job, db, job_id, current_user.id)


@router.post("/{job_id}/publish")
def generation_publish_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    return _transition(publish_generation_job, db, job_id, current_user.id)


@router.post("/{job_id}/cancel")
def generation_cancel_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_generation_role(current_user)
    return _transition(cancel_generation_job, db, job_id, current_user.id)


def _transition(handler, db: Session, job_id: int, actor_user_id: int):
    try:
        return generation_job_to_dict(handler(db, job_id, actor_user_id))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
