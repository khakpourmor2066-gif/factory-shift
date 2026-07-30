from sqlalchemy.orm import Session

from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.users.model import User
from app.modules.users.repository import create_user, list_users
from app.modules.users.schema import UserCreate, UserRoleUpdate
from app.modules.change_management.schemas.change_management import AuditLogCreate


def register_user(db: Session, user_in: UserCreate):
    return create_user(db, user_in)


def get_users(db: Session):
    return list_users(db)


def update_user_role(db: Session, user: User, user_role: UserRoleUpdate) -> User:
    before_role = user.role
    user.role = user_role.role
    db.commit()
    db.refresh(user)
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=user.id,
            action="user_role_updated",
            before_value=before_role,
            after_value=user.role,
        ),
    )
    return user


def unlink_messenger_account(db: Session, user: User) -> User:
    previous_messenger_user_id = user.messenger_user_id
    user.messenger_user_id = None
    db.commit()
    db.refresh(user)
    create_audit_log(
        db,
        AuditLogCreate(
            user_id=user.id,
            action="messenger_account_logged_out",
            before_value=previous_messenger_user_id,
            after_value=None,
        ),
    )
    return user
