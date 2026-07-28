from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.database.connection import Base, engine
from app.modules.access_requests.model import AccessRequest
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User
from app.modules.webhook_logs.model import WebhookLog

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
