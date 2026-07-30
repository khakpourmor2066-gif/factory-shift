from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database.connection import Base


class ScheduleGenerationJob(Base):
    __tablename__ = "schedule_generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("employee_shift_assignments.id"), nullable=False)
    pattern_id = Column(Integer, ForeignKey("shift_patterns.id"), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    preview_payload = Column(Text, nullable=False)
    total_days = Column(Integer, nullable=False)
    missing_days = Column(Integer, nullable=False)
    created_schedules = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
