from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user
from app.modules.employee_view.schema import MyScheduleRead
from app.modules.employee_view.service import get_my_schedule
from app.modules.users.model import User

router = APIRouter(prefix="/me", tags=["employee-view"])


@router.get("/schedule", response_model=MyScheduleRead)
def my_schedule_endpoint(
    from_date: date,
    to_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_schedule(db, current_user, from_date, to_date)
