from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    name: str


class DepartmentRead(DepartmentCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
