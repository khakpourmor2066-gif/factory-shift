from sqlalchemy.orm import Session

from app.modules.attendance.model import AttendanceRecord
from app.modules.attendance.schemas.attendance import AttendanceImportRow


def import_attendance_rows(db: Session, rows: list[AttendanceImportRow], source_file: str | None = None) -> list[AttendanceRecord]:
    records = []
    for row in rows:
        record = AttendanceRecord(
            employee_id=row.employee_id,
            record_date=row.record_date,
            status=row.status,
            check_in=row.check_in,
            check_out=row.check_out,
            source_file=source_file,
            imported=True,
        )
        db.add(record)
        records.append(record)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


def list_attendance_by_employee(db: Session, employee_id: int) -> list[AttendanceRecord]:
    return db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == employee_id).order_by(AttendanceRecord.record_date).all()
