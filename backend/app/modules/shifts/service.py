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
    pattern_days = get_pattern_days(db, assignment.pattern_id)
    records = generate_schedule_records(
        assignment=assignment,
        pattern_days=pattern_days,
        from_date=request.from_date,
        to_date=request.to_date,
        publish=request.publish,
    )
    return save_schedules(db, records)


def get_schedule(db: Session, employee_id: int, from_date, to_date):
    return list_employee_schedule(db, employee_id, from_date, to_date)
