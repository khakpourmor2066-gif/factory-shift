from sqlalchemy.orm import Session

from app.modules.employees.model import Employee
from app.modules.employees.schema import EmployeeCreate


def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    employee = Employee(**employee_in.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def list_employees(db: Session) -> list[Employee]:
    return db.query(Employee).order_by(Employee.id).all()


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def link_user(db: Session, employee: Employee, user_id: int) -> Employee:
    employee.user_id = user_id
    db.commit()
    db.refresh(employee)
    return employee
