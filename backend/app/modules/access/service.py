from sqlalchemy.orm import Session

from app.modules.employees.model import Employee
from app.modules.users.model import User


def get_employee_for_user(db: Session, user: User) -> Employee | None:
    return db.query(Employee).filter(Employee.user_id == user.id).first()
