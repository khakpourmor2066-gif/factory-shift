from datetime import date

from pydantic import BaseModel


class SupervisorScheduleEmployee(BaseModel):
    employee_id: int
    full_name: str
    status: str


class SupervisorScheduleRead(BaseModel):
    date: date
    employees: list[SupervisorScheduleEmployee]
