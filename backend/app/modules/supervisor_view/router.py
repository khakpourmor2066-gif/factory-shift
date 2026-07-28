from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user
from app.modules.supervisor_view.schema import SupervisorScheduleRead
from app.modules.supervisor_view.service import get_supervisor_schedule
from app.modules.users.model import User

router = APIRouter(prefix="/supervisor", tags=["supervisor-view"])


@router.get("/schedule", response_model=SupervisorScheduleRead)
def supervisor_schedule_endpoint(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_supervisor_schedule(db, current_user, target_date)
