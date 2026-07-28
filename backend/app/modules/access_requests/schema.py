from datetime import datetime

from pydantic import BaseModel


class AccessRequestRead(BaseModel):
    id: int
    platform: str
    messenger_user_id: str
    latest_text: str | None = None
    status: str
    request_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccessRequestReport(BaseModel):
    counts: dict[str, int]
    total: int
    latest: list[AccessRequestRead]
