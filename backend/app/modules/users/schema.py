from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    mobile: str
    role: str
    messenger_user_id: str | None = None


class UserRoleUpdate(BaseModel):
    role: str


class UserRead(UserCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)
