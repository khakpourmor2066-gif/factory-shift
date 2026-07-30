from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class ShiftPattern(Base):
    __tablename__ = "shift_patterns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    cycle_length = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    days = relationship("ShiftPatternDay", cascade="all, delete-orphan")


class ShiftPatternDay(Base):
    __tablename__ = "shift_pattern_days"

    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(Integer, ForeignKey("shift_patterns.id"), nullable=False)
    day_index = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)


class EmployeeShiftAssignment(Base):
    __tablename__ = "employee_shift_assignments"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    pattern_id = Column(Integer, ForeignKey("shift_patterns.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pattern = relationship("ShiftPattern")


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_schedules_employee_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)
    shift_name = Column(String(100), nullable=True)
    shift_code = Column(String(50), nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    location = Column(String(150), nullable=True)
    note = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    generated_from = Column(String(50), nullable=False, default="GENERATOR")
    published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
