from pydantic import BaseModel, ConfigDict


class AttendanceImportRow(BaseModel):
    employee_id: int
    record_date: str
    status: str
    check_in: str | None = None
    check_out: str | None = None


class AttendanceRecordRead(AttendanceImportRow):
    id: int
    source_file: str | None = None
    imported: bool
    model_config = ConfigDict(from_attributes=True)
