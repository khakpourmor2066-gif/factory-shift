from datetime import date

from pydantic import BaseModel


class MyScheduleDay(BaseModel):
    date: date
    status: str
    published: bool


class MyScheduleRead(BaseModel):
    employee_id: int
    employee_name: str
    days: list[MyScheduleDay]
