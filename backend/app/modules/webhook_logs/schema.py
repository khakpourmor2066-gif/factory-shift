from datetime import datetime

from pydantic import BaseModel


class WebhookLogRead(BaseModel):
    id: int
    platform: str
    messenger_user_id: str
    direction: str
    event_type: str
    request_text: str | None = None
    response_status: str | None = None
    response_text: str | None = None
    sent_status: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookLogReport(BaseModel):
    counts: dict[str, int]
    total: int
    latest: list[WebhookLogRead]
