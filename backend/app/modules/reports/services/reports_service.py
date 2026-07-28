from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.attendance.model import AttendanceRecord
from app.modules.shifts.model import Schedule


def get_daily_staff_report(db: Session, target_date: str) -> list[dict]:
    rows = (
        db.query(Schedule.status, func.count(Schedule.id))
        .filter(Schedule.date == target_date)
        .group_by(Schedule.status)
        .all()
    )
    return [{"date": target_date, "status": status, "count": count} for status, count in rows]


def get_monthly_summary(db: Session, employee_id: int | None = None) -> dict:
    schedule_query = db.query(Schedule)
    attendance_query = db.query(AttendanceRecord)
    if employee_id is not None:
        schedule_query = schedule_query.filter(Schedule.employee_id == employee_id)
        attendance_query = attendance_query.filter(AttendanceRecord.employee_id == employee_id)

    work_days = schedule_query.filter(Schedule.status == "WORK").count()
    rest_days = schedule_query.filter(Schedule.status == "REST").count()
    attendance_days = attendance_query.count()

    return {
        "employee_id": employee_id,
        "work_days": work_days,
        "rest_days": rest_days,
        "attendance_days": attendance_days,
    }
