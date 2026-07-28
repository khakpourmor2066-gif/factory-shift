from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ScheduleExceptionCreate(BaseModel):
    employee_id: int
    schedule_date: date
    before_status: str
    after_status: str
    reason: str | None = None
    created_by: int


class ScheduleExceptionRead(ScheduleExceptionCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    user_id: int
    message: str


class NotificationRead(NotificationCreate):
    id: int
    sent_status: bool
    read_status: bool
    read_time: datetime | None
    model_config = ConfigDict(from_attributes=True)


class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    before_value: str | None = None
    after_value: str | None = None


class AuditLogRead(AuditLogCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
