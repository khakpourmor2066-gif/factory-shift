from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_at: datetime | None = None


class ApiTokenRead(BaseModel):
    id: int
    user_id: int
    name: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApiTokenCreated(ApiTokenRead):
    token: str
