from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.modules.auth_tokens.service import WEB_SESSION_COOKIE, authenticate_api_token
from app.modules.users.model import User


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    web_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE),
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    if authorization is not None:
        scheme, separator, raw_token = authorization.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid Authorization header",
            )
        api_token = authenticate_api_token(db, raw_token)
        if api_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API token")
        user = db.query(User).filter(User.id == api_token.user_id).first()
    elif web_session is not None:
        api_token = authenticate_api_token(db, web_session)
        if api_token is None or api_token.name != "bale-web-session":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid web session")
        user = db.query(User).filter(User.id == api_token.user_id).first()
    elif settings.allow_legacy_user_header:
        if x_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token or X-User-Id header is required",
            )
        user = db.query(User).filter(User.id == x_user_id).first()
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required")

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="active user not found")

    return user


def require_roles(user: User, allowed_roles: set[str]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
