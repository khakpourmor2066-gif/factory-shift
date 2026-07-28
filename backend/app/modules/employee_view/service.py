from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.access.permissions import can_view_own_schedule
from app.modules.access.service import get_employee_for_user
from app.modules.shifts.model import Schedule
from app.modules.users.model import User


def get_my_schedule(db: Session, user: User, from_date: date, to_date: date) -> dict:
    if not can_view_own_schedule(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")

    employee = get_employee_for_user(db, user)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employee profile not linked")

    schedules = (
        db.query(Schedule)
        .filter(Schedule.employee_id == employee.id)
        .filter(Schedule.date >= from_date)
        .filter(Schedule.date <= to_date)
        .filter(Schedule.published.is_(True))
        .order_by(Schedule.date)
        .all()
    )

    return {
        "employee_id": employee.id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "days": [
            {
                "date": schedule.date,
                "status": schedule.status,
                "published": schedule.published,
            }
            for schedule in schedules
        ],
    }
