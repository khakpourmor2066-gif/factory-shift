from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ScheduleGenerationPreviewCreate(BaseModel):
    employee_id: int
    assignment_id: int
    from_date: date
    to_date: date


class ScheduleGenerationItem(BaseModel):
    date: date
    status: str


class ScheduleGenerationJobRead(BaseModel):
    id: int
    employee_id: int
    assignment_id: int
    pattern_id: int
    from_date: date
    to_date: date
    status: str
    total_days: int
    missing_days: int
    existing_days: int
    created_schedules: int
    preview: list[ScheduleGenerationItem]
    created_by: int
    created_at: datetime
    completed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
