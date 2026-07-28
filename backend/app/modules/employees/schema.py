from pydantic import BaseModel, ConfigDict


class EmployeeCreate(BaseModel):
    personnel_code: str
    first_name: str
    last_name: str
    mobile: str
    department_id: int
    supervisor_id: int | None = None
    user_id: int | None = None


class EmployeeRead(EmployeeCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class LinkEmployeeUserRequest(BaseModel):
    user_id: int
