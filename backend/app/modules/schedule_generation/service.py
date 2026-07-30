from datetime import date, datetime, timedelta, timezone
import json

from sqlalchemy.orm import Session

from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.employees.model import Employee
from app.modules.schedule_generation.model import ScheduleGenerationJob
from app.modules.schedule_generation.schema import ScheduleGenerationPreviewCreate
from app.modules.shifts.generator import generate_schedule_records
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern
from app.modules.shifts.repository import get_pattern_days, list_employee_schedule


MAX_GENERATION_DAYS = 366


def list_generation_options(db: Session) -> dict:
    employees = (
        db.query(Employee)
        .filter(Employee.is_active.is_(True))
        .order_by(Employee.personnel_code)
        .all()
    )
    assignments = (
        db.query(EmployeeShiftAssignment, ShiftPattern)
        .join(ShiftPattern, ShiftPattern.id == EmployeeShiftAssignment.pattern_id)
        .order_by(EmployeeShiftAssignment.employee_id, EmployeeShiftAssignment.start_date)
        .all()
    )
    assignments_by_employee: dict[int, list[dict]] = {}
    for assignment, pattern in assignments:
        assignments_by_employee.setdefault(assignment.employee_id, []).append(
            {
                "id": assignment.id,
                "pattern_id": pattern.id,
                "pattern_name": pattern.name,
                "start_date": assignment.start_date.isoformat(),
                "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
            }
        )
    return {
        "employees": [
            {
                "id": employee.id,
                "personnel_code": employee.personnel_code,
                "full_name": f"{employee.first_name} {employee.last_name}",
                "assignments": assignments_by_employee.get(employee.id, []),
            }
            for employee in employees
            if assignments_by_employee.get(employee.id)
        ]
    }


def create_generation_preview(
    db: Session,
    payload: ScheduleGenerationPreviewCreate,
    created_by: int,
) -> ScheduleGenerationJob:
    assignment = _validate_request(db, payload)
    pattern_days = get_pattern_days(db, assignment.pattern_id)
    generated = generate_schedule_records(
        assignment=assignment,
        pattern_days=pattern_days,
        from_date=payload.from_date,
        to_date=payload.to_date,
        publish=False,
    )
    existing_dates = {
        schedule.date
        for schedule in list_employee_schedule(
            db,
            payload.employee_id,
            payload.from_date,
            payload.to_date,
        )
    }
    preview = [
        {"date": record.date.isoformat(), "status": record.status}
        for record in generated
        if record.date not in existing_dates
    ]
    job = ScheduleGenerationJob(
        employee_id=payload.employee_id,
        assignment_id=payload.assignment_id,
        pattern_id=assignment.pattern_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        status="PENDING",
        preview_payload=json.dumps(preview, ensure_ascii=False),
        total_days=len(generated),
        missing_days=len(preview),
        created_schedules=0,
        created_by=created_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _audit(db, created_by, "schedule_generation_previewed", f"job={job.id},missing={job.missing_days}")
    return job


def get_generation_job(db: Session, job_id: int) -> ScheduleGenerationJob:
    job = db.query(ScheduleGenerationJob).filter(ScheduleGenerationJob.id == job_id).first()
    if job is None:
        raise ValueError("schedule generation job not found")
    return job


def confirm_generation_job(db: Session, job_id: int, actor_user_id: int) -> ScheduleGenerationJob:
    job = _lock_job(db, job_id)
    if job.status == "CONFIRMED":
        return job
    if job.status != "PENDING":
        raise ValueError(f"cannot confirm job in {job.status} status")
    created = _create_missing_schedules(db, job, publish=False)
    job.status = "CONFIRMED"
    job.created_schedules = created
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    _audit(db, actor_user_id, "schedule_generation_confirmed", f"job={job.id},created={created}")
    return job


def publish_generation_job(db: Session, job_id: int, actor_user_id: int) -> ScheduleGenerationJob:
    job = _lock_job(db, job_id)
    if job.status == "PUBLISHED":
        return job
    if job.status == "PENDING":
        job.created_schedules = _create_missing_schedules(db, job, publish=True)
    elif job.status == "CONFIRMED":
        (
            db.query(Schedule)
            .filter(Schedule.generated_from == _generation_source(job.id))
            .update({Schedule.published: True}, synchronize_session=False)
        )
    else:
        raise ValueError(f"cannot publish job in {job.status} status")
    job.status = "PUBLISHED"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    _audit(
        db,
        actor_user_id,
        "schedule_generation_published",
        f"job={job.id},created={job.created_schedules}",
    )
    return job


def cancel_generation_job(db: Session, job_id: int, actor_user_id: int) -> ScheduleGenerationJob:
    job = _lock_job(db, job_id)
    if job.status == "CANCELLED":
        return job
    if job.status != "PENDING":
        raise ValueError(f"cannot cancel job in {job.status} status")
    job.status = "CANCELLED"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    _audit(db, actor_user_id, "schedule_generation_cancelled", f"job={job.id}")
    return job


def generation_job_to_dict(job: ScheduleGenerationJob) -> dict:
    preview = json.loads(job.preview_payload)
    return {
        "id": job.id,
        "employee_id": job.employee_id,
        "assignment_id": job.assignment_id,
        "pattern_id": job.pattern_id,
        "from_date": job.from_date.isoformat(),
        "to_date": job.to_date.isoformat(),
        "status": job.status,
        "total_days": job.total_days,
        "missing_days": job.missing_days,
        "existing_days": job.total_days - job.missing_days,
        "created_schedules": job.created_schedules,
        "preview": preview,
        "created_by": job.created_by,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def quick_range_for_assignment(
    assignment: EmployeeShiftAssignment,
    range_key: str,
    today: date | None = None,
) -> tuple[date, date]:
    current_date = today or date.today()
    start_date = max(current_date, assignment.start_date)
    if range_key == "7D":
        end_date = start_date + timedelta(days=6)
    elif range_key == "CURRENT_MONTH":
        end_date = _month_end(start_date)
    elif range_key == "NEXT_MONTH":
        next_month_start = _month_end(current_date) + timedelta(days=1)
        start_date = max(next_month_start, assignment.start_date)
        end_date = _month_end(start_date)
    else:
        raise ValueError("invalid generation range")
    if assignment.end_date is not None:
        end_date = min(end_date, assignment.end_date)
    if start_date > end_date:
        raise ValueError("assignment does not cover selected range")
    return start_date, end_date


def get_assignment_for_generation(db: Session, assignment_id: int) -> EmployeeShiftAssignment:
    assignment = (
        db.query(EmployeeShiftAssignment)
        .filter(EmployeeShiftAssignment.id == assignment_id)
        .first()
    )
    if assignment is None:
        raise ValueError("assignment not found")
    return assignment


def _validate_request(
    db: Session,
    payload: ScheduleGenerationPreviewCreate,
) -> EmployeeShiftAssignment:
    assignment = get_assignment_for_generation(db, payload.assignment_id)
    if assignment.employee_id != payload.employee_id:
        raise ValueError("assignment does not belong to employee")
    if payload.from_date > payload.to_date:
        raise ValueError("from_date must be before or equal to to_date")
    if (payload.to_date - payload.from_date).days + 1 > MAX_GENERATION_DAYS:
        raise ValueError(f"generation range cannot exceed {MAX_GENERATION_DAYS} days")
    if payload.from_date < assignment.start_date:
        raise ValueError("from_date cannot be before assignment start_date")
    if assignment.end_date is not None and payload.to_date > assignment.end_date:
        raise ValueError("to_date cannot be after assignment end_date")
    return assignment


def _lock_job(db: Session, job_id: int) -> ScheduleGenerationJob:
    job = (
        db.query(ScheduleGenerationJob)
        .filter(ScheduleGenerationJob.id == job_id)
        .with_for_update()
        .first()
    )
    if job is None:
        raise ValueError("schedule generation job not found")
    return job


def _create_missing_schedules(db: Session, job: ScheduleGenerationJob, publish: bool) -> int:
    preview = json.loads(job.preview_payload)
    existing_dates = {
        schedule.date
        for schedule in list_employee_schedule(db, job.employee_id, job.from_date, job.to_date)
    }
    records = [
        Schedule(
            employee_id=job.employee_id,
            date=date.fromisoformat(item["date"]),
            status=item["status"],
            generated_from=_generation_source(job.id),
            published=publish,
        )
        for item in preview
        if date.fromisoformat(item["date"]) not in existing_dates
    ]
    db.add_all(records)
    db.flush()
    return len(records)


def _generation_source(job_id: int) -> str:
    return f"GEN_JOB:{job_id}"


def _month_end(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1) - timedelta(days=1)
    return date(value.year, value.month + 1, 1) - timedelta(days=1)


def _audit(db: Session, user_id: int, action: str, after_value: str) -> None:
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=user_id,
            action=action,
            before_value=None,
            after_value=after_value,
        ),
    )
