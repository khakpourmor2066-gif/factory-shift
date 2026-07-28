from datetime import date

from sqlalchemy.orm import Session

from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.shifts.schema import EmployeeShiftAssignmentCreate, ShiftPatternCreate


def create_shift_pattern(db: Session, pattern_in: ShiftPatternCreate) -> ShiftPattern:
    pattern = ShiftPattern(
        name=pattern_in.name,
        cycle_length=len(pattern_in.days),
        description=pattern_in.description,
    )
    db.add(pattern)
    db.flush()
    for index, status in enumerate(pattern_in.days):
        db.add(ShiftPatternDay(pattern_id=pattern.id, day_index=index, status=status))
    db.commit()
    db.refresh(pattern)
    return pattern


def list_shift_patterns(db: Session) -> list[ShiftPattern]:
    return db.query(ShiftPattern).order_by(ShiftPattern.id).all()


def create_assignment(db: Session, assignment_in: EmployeeShiftAssignmentCreate) -> EmployeeShiftAssignment:
    assignment = EmployeeShiftAssignment(**assignment_in.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_assignment(db: Session, assignment_id: int) -> EmployeeShiftAssignment | None:
    return db.query(EmployeeShiftAssignment).filter(EmployeeShiftAssignment.id == assignment_id).first()


def get_pattern_days(db: Session, pattern_id: int) -> list[ShiftPatternDay]:
    return (
        db.query(ShiftPatternDay)
        .filter(ShiftPatternDay.pattern_id == pattern_id)
        .order_by(ShiftPatternDay.day_index)
        .all()
    )


def save_schedules(db: Session, schedules: list[Schedule]) -> list[Schedule]:
    db.add_all(schedules)
    db.commit()
    for schedule in schedules:
        db.refresh(schedule)
    return schedules


def list_employee_schedule(db: Session, employee_id: int, from_date: date, to_date: date) -> list[Schedule]:
    return (
        db.query(Schedule)
        .filter(Schedule.employee_id == employee_id)
        .filter(Schedule.date >= from_date)
        .filter(Schedule.date <= to_date)
        .order_by(Schedule.date)
        .all()
    )
