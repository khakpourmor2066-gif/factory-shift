from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.access.permissions import can_view_supervisor_schedule
from app.modules.access.service import get_employee_for_user
from app.modules.employees.model import Employee
from app.modules.shifts.model import Schedule
from app.modules.users.model import User


def get_supervisor_schedule(db: Session, user: User, target_date: date) -> dict:
    if not can_view_supervisor_schedule(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")

    query = (
        db.query(Employee, Schedule)
        .join(Schedule, Schedule.employee_id == Employee.id)
        .filter(Employee.is_active.is_(True))
        .filter(Schedule.date == target_date)
        .filter(Schedule.published.is_(True))
    )
    if user.role == "SUPERVISOR":
        supervisor_employee = get_employee_for_user(db, user)
        if supervisor_employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="supervisor employee profile not linked",
            )
        query = query.filter(Employee.supervisor_id == supervisor_employee.id)
    rows = query.order_by(Employee.id).all()

    return {
        "date": target_date,
        "employees": [
            {
                "employee_id": employee.id,
                "full_name": f"{employee.first_name} {employee.last_name}",
                "status": schedule.status,
            }
            for employee, schedule in rows
        ],
    }
