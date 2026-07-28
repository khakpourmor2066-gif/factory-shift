from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.database.connection import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    record_date = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    check_in = Column(String(20), nullable=True)
    check_out = Column(String(20), nullable=True)
    source_file = Column(String(255), nullable=True)
    imported = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
