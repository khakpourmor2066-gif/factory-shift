from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.data_imports.schema import (
    ImportErrorRead,
    ImportJobRead,
    ImportPreviewResponse,
    ImportRecordRead,
    ImportTemplateRead,
)
from app.modules.data_imports.service import (
    confirm_import,
    create_import_preview,
    employee_template,
    get_import_job,
    list_import_errors,
    list_import_jobs,
    list_import_records,
    reject_import,
    rollback_import,
    shift_template,
)
from app.modules.users.model import User


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/employees/preview", response_model=ImportPreviewResponse)
async def preview_employee_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "ADMIN"})
    return await _preview(db, current_user, "EMPLOYEE", file)


@router.post("/shifts/preview", response_model=ImportPreviewResponse)
async def preview_shift_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN"})
    return await _preview(db, current_user, "SHIFT", file)


@router.get("", response_model=list[ImportJobRead])
def list_imports(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "SUPERVISOR", "ADMIN"})
    return list_import_jobs(db, limit=min(max(limit, 1), 500))


@router.get("/templates/employees", response_model=ImportTemplateRead)
def get_employee_template(
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "ADMIN"})
    return ImportTemplateRead(
        filename="employees_template.csv",
        content_type="text/csv",
        content=employee_template(),
    )


@router.get("/templates/shifts", response_model=ImportTemplateRead)
def get_shift_template(
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN"})
    return ImportTemplateRead(
        filename="shifts_template.csv",
        content_type="text/csv",
        content=shift_template(),
    )


@router.get("/{job_id}", response_model=ImportJobRead)
def get_import(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "SUPERVISOR", "ADMIN"})
    return _job_or_404(db, job_id)


@router.get("/{job_id}/errors", response_model=list[ImportErrorRead])
def get_import_errors(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "SUPERVISOR", "ADMIN"})
    try:
        return list_import_errors(db, job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{job_id}/records", response_model=list[ImportRecordRead])
def get_import_records(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"HR", "SUPERVISOR", "ADMIN"})
    try:
        return list_import_records(db, job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{job_id}/confirm", response_model=ImportJobRead)
def confirm_import_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _require_job_role(current_user, get_import_job(db, job_id))
        return confirm_import(db, job_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{job_id}/reject", response_model=ImportJobRead)
def reject_import_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _require_job_role(current_user, get_import_job(db, job_id))
        return reject_import(db, job_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{job_id}/rollback", response_model=ImportJobRead)
def rollback_import_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        job = get_import_job(db, job_id)
        _require_job_role(current_user, job)
        return rollback_import(db, job_id, current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


async def _preview(
    db: Session,
    current_user: User,
    import_type: str,
    file: UploadFile,
) -> ImportPreviewResponse:
    try:
        content = await file.read(settings.max_import_bytes + 1)
        if len(content) > settings.max_import_bytes:
            raise ValueError(f"file exceeds {settings.max_import_bytes} bytes")
        job = create_import_preview(
            db,
            import_type=import_type,
            filename=file.filename or "upload",
            content=content,
            created_by=current_user.id,
        )
        return ImportPreviewResponse(job=job, errors=list_import_errors(db, job.id))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _job_or_404(db: Session, job_id: int):
    try:
        return get_import_job(db, job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _require_job_role(current_user: User, job) -> None:
    allowed_roles = {"ADMIN"}
    if job.import_type == "EMPLOYEE":
        allowed_roles.add("HR")
    elif job.import_type == "SHIFT":
        allowed_roles.add("SUPERVISOR")
    require_roles(current_user, allowed_roles)
