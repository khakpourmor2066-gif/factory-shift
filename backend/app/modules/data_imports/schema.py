from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobRead(BaseModel):
    id: int
    import_type: str
    filename: str
    status: str
    created_by: int
    total_rows: int
    valid_rows: int
    imported_rows: int
    rejected_rows: int
    created_at: datetime
    completed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ImportErrorRead(BaseModel):
    id: int
    job_id: int
    row_number: int
    field_name: str | None
    error_code: str
    message: str
    model_config = ConfigDict(from_attributes=True)


class ImportPreviewResponse(BaseModel):
    job: ImportJobRead
    errors: list[ImportErrorRead]


class ImportRecordRead(BaseModel):
    row_number: int
    data: dict


class ImportTemplateRead(BaseModel):
    filename: str
    content_type: str
    content: str
