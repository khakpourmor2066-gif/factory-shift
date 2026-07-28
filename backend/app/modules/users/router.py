from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.users.model import User
from app.modules.users.schema import UserCreate, UserRead, UserRoleUpdate
from app.modules.users.service import get_users, register_user, update_user_role

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead)
def create_user_endpoint(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return register_user(db, user_in)


@router.get("", response_model=list[UserRead])
def list_users_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    return get_users(db)


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role_endpoint(
    user_id: int,
    user_role: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return update_user_role(db, user, user_role)
