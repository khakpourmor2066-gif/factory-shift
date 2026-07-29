from datetime import date, time

from pydantic import BaseModel, ConfigDict


class ShiftPatternDayCreate(BaseModel):
    day_index: int
    status: str


class ShiftPatternCreate(BaseModel):
    name: str
    days: list[str]
    description: str | None = None


class ShiftPatternRead(BaseModel):
    id: int
    name: str
    cycle_length: int
    description: str | None
    model_config = ConfigDict(from_attributes=True)


class EmployeeShiftAssignmentCreate(BaseModel):
    employee_id: int
    pattern_id: int
    start_date: date
    end_date: date | None = None


class EmployeeShiftAssignmentRead(EmployeeShiftAssignmentCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ScheduleGenerateRequest(BaseModel):
    employee_id: int
    assignment_id: int
    from_date: date
    to_date: date
    publish: bool = False


class ScheduleRead(BaseModel):
    id: int
    employee_id: int
    date: date
    status: str
    shift_name: str | None = None
    shift_code: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    note: str | None = None
    source: str | None = None
    published: bool
    model_config = ConfigDict(from_attributes=True)
