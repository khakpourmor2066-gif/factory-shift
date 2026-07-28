from pydantic import BaseModel


class DailyStaffReportItem(BaseModel):
    date: str
    status: str
    count: int


class MonthlySummaryReport(BaseModel):
    employee_id: int | None = None
    work_days: int
    rest_days: int
    attendance_days: int
