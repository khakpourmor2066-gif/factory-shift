from fastapi import FastAPI, HTTPException, Response
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.observability import render_metrics, request_observability_middleware
from app.database.connection import Base, SessionLocal, engine
from app.modules.access_requests.model import AccessRequest
from app.modules.auth_tokens.model import ApiToken
from app.modules.data_imports.model import ImportError, ImportJob
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User
from app.modules.webhook_logs.model import WebhookLog

if settings.auto_create_tables:
    Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.middleware("http")(request_observability_middleware)
app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/live")
def liveness_check():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as error:
        raise HTTPException(status_code=503, detail="database unavailable") from error
    finally:
        db.close()


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")
