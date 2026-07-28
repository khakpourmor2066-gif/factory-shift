from sqlalchemy.orm import Session

from app.modules.departments.model import Department
from app.modules.departments.schema import DepartmentCreate


def create_department(db: Session, department_in: DepartmentCreate) -> Department:
    department = Department(name=department_in.name)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def list_departments(db: Session) -> list[Department]:
    return db.query(Department).order_by(Department.id).all()
