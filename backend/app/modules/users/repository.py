from sqlalchemy.orm import Session

from app.modules.users.model import User
from app.modules.users.schema import UserCreate


def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        mobile=user_in.mobile,
        role=user_in.role,
        messenger_user_id=user_in.messenger_user_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id).all()
