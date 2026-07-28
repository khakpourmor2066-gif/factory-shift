from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.departments.schema import DepartmentCreate, DepartmentRead
from app.modules.departments.service import get_departments, register_department

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("", response_model=DepartmentRead)
def create_department_endpoint(department_in: DepartmentCreate, db: Session = Depends(get_db)):
    return register_department(db, department_in)


@router.get("", response_model=list[DepartmentRead])
def list_departments_endpoint(db: Session = Depends(get_db)):
    return get_departments(db)
