from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.employees.schema import EmployeeCreate, EmployeeRead, LinkEmployeeUserRequest
from app.modules.employees.service import get_employees, link_employee_to_user, register_employee
from app.modules.users.model import User

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead)
def create_employee_endpoint(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return register_employee(db, employee_in)


@router.get("", response_model=list[EmployeeRead])
def list_employees_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return get_employees(db)


@router.post("/{employee_id}/link-user", response_model=EmployeeRead)
def link_employee_user_endpoint(
    employee_id: int,
    request: LinkEmployeeUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return link_employee_to_user(db, employee_id, request.user_id)
