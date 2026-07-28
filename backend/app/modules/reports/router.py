from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.reports.services.reports_service import get_daily_staff_report, get_monthly_summary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def daily_report_endpoint(date: str, db: Session = Depends(get_db)):
    return get_daily_staff_report(db, date)


@router.get("/summary")
def monthly_summary_endpoint(employee_id: int | None = None, db: Session = Depends(get_db)):
    return get_monthly_summary(db, employee_id)
