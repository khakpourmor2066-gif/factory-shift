from sqlalchemy.orm import Session

from app.modules.departments.repository import create_department, list_departments
from app.modules.departments.schema import DepartmentCreate


def register_department(db: Session, department_in: DepartmentCreate):
    return create_department(db, department_in)


def get_departments(db: Session):
    return list_departments(db)
