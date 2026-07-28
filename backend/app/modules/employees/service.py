from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.employees.repository import create_employee, get_employee, link_user, list_employees
from app.modules.employees.schema import EmployeeCreate


def register_employee(db: Session, employee_in: EmployeeCreate):
    return create_employee(db, employee_in)


def get_employees(db: Session):
    return list_employees(db)


def link_employee_to_user(db: Session, employee_id: int, user_id: int):
    employee = get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employee not found")
    before_value = str(employee.user_id)
    result = link_user(db, employee, user_id)
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=user_id,
            action="employee_user_linked",
            before_value=before_value,
            after_value=str(user_id),
        ),
    )
    return result
