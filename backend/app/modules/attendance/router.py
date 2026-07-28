from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.attendance.schemas.attendance import AttendanceImportRow, AttendanceRecordRead
from app.modules.attendance.services.attendance_service import import_attendance_rows, list_attendance_by_employee

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/import", response_model=list[AttendanceRecordRead])
def import_attendance_endpoint(rows: list[AttendanceImportRow], source_file: str | None = None, db: Session = Depends(get_db)):
    return import_attendance_rows(db, rows, source_file)


@router.get("/employee/{employee_id}", response_model=list[AttendanceRecordRead])
def attendance_by_employee_endpoint(employee_id: int, db: Session = Depends(get_db)):
    return list_attendance_by_employee(db, employee_id)
