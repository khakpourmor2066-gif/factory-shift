from sqlalchemy.orm import Session

from app.modules.shifts.generator import generate_schedule_records
from app.modules.shifts.repository import (
    create_assignment,
    create_shift_pattern,
    get_assignment,
    get_pattern_days,
    list_employee_schedule,
    list_shift_patterns,
    save_schedules,
)
from app.modules.shifts.schema import EmployeeShiftAssignmentCreate, ScheduleGenerateRequest, ShiftPatternCreate


def register_shift_pattern(db: Session, pattern_in: ShiftPatternCreate):
    return create_shift_pattern(db, pattern_in)


def get_shift_patterns(db: Session):
    return list_shift_patterns(db)


def register_assignment(db: Session, assignment_in: EmployeeShiftAssignmentCreate):
    return create_assignment(db, assignment_in)


def generate_schedule(db: Session, request: ScheduleGenerateRequest):
    assignment = get_assignment(db, request.assignment_id)
    if assignment is None:
        raise ValueError("assignment not found")
    if assignment.employee_id != request.employee_id:
        raise ValueError("assignment does not belong to employee")
    if request.from_date < assignment.start_date:
        raise ValueError("from_date cannot be before assignment start_date")
    if assignment.end_date is not None and request.to_date > assignment.end_date:
        raise ValueError("to_date cannot be after assignment end_date")
    pattern_days = get_pattern_days(db, assignment.pattern_id)
    records = generate_schedule_records(
        assignment=assignment,
        pattern_days=pattern_days,
        from_date=request.from_date,
        to_date=request.to_date,
        publish=request.publish,
    )
    existing_dates = {
        schedule.date
        for schedule in list_employee_schedule(
            db,
            request.employee_id,
            request.from_date,
            request.to_date,
        )
    }
    missing_records = [record for record in records if record.date not in existing_dates]
    if not missing_records:
        return []
    return save_schedules(db, missing_records)


def get_schedule(db: Session, employee_id: int, from_date, to_date):
    return list_employee_schedule(db, employee_id, from_date, to_date)
