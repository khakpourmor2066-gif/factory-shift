from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.shifts.schema import (
    EmployeeShiftAssignmentCreate,
    EmployeeShiftAssignmentRead,
    ScheduleGenerateRequest,
    ScheduleRead,
    ShiftPatternCreate,
    ShiftPatternRead,
)
from app.modules.shifts.service import (
    generate_schedule,
    get_schedule,
    get_shift_patterns,
    register_assignment,
    register_shift_pattern,
)
from app.modules.users.model import User

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.post("/patterns", response_model=ShiftPatternRead)
def create_pattern_endpoint(
    pattern_in: ShiftPatternCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN"})
    return register_shift_pattern(db, pattern_in)


@router.get("/patterns", response_model=list[ShiftPatternRead])
def list_patterns_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return get_shift_patterns(db)


@router.post("/assignments", response_model=EmployeeShiftAssignmentRead)
def create_assignment_endpoint(
    assignment_in: EmployeeShiftAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN"})
    return register_assignment(db, assignment_in)


@router.post("/generate", response_model=list[ScheduleRead])
def generate_schedule_endpoint(
    request: ScheduleGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN"})
    try:
        return generate_schedule(db, request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/schedule/{employee_id}", response_model=list[ScheduleRead])
def get_employee_schedule_endpoint(
    employee_id: int,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return get_schedule(db, employee_id, from_date, to_date)
