import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.modules.auth_tokens.model import ApiToken
from app.modules.change_management.model import AuditLog


def create_api_token(
    db: Session,
    user_id: int,
    name: str,
    expires_at: datetime | None,
) -> tuple[ApiToken, str]:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("token name is required")
    if expires_at is not None:
        normalized_expiry = expires_at
        if normalized_expiry.tzinfo is None:
            normalized_expiry = normalized_expiry.replace(tzinfo=UTC)
        if normalized_expiry <= datetime.now(UTC):
            raise ValueError("token expiration must be in the future")
    raw_token = secrets.token_urlsafe(32)
    token = ApiToken(
        user_id=user_id,
        name=normalized_name,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
        is_active=True,
    )
    db.add(token)
    db.flush()
    db.add(
        AuditLog(
            user_id=user_id,
            action="api_token_created",
            after_value=f"token_id={token.id},name={token.name}",
        )
    )
    db.commit()
    db.refresh(token)
    return token, raw_token


def create_temporary_web_token(
    db: Session,
    user_id: int,
    *,
    lifetime_minutes: int = 15,
) -> tuple[ApiToken, str]:
    token_name = "bale-web-temporary"
    active_tokens = (
        db.query(ApiToken)
        .filter(
            ApiToken.user_id == user_id,
            ApiToken.name == token_name,
            ApiToken.is_active.is_(True),
        )
        .all()
    )
    for token in active_tokens:
        token.is_active = False
    if active_tokens:
        db.commit()
    return create_api_token(
        db,
        user_id=user_id,
        name=token_name,
        expires_at=datetime.now(UTC) + timedelta(minutes=lifetime_minutes),
    )


def authenticate_api_token(db: Session, raw_token: str):
    token = (
        db.query(ApiToken)
        .filter(ApiToken.token_hash == hash_token(raw_token), ApiToken.is_active.is_(True))
        .first()
    )
    if token is None:
        return None
    expires_at = token.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return None
    token.last_used_at = datetime.now(UTC)
    db.commit()
    return token


def list_api_tokens(db: Session, user_id: int) -> list[ApiToken]:
    return db.query(ApiToken).filter(ApiToken.user_id == user_id).order_by(ApiToken.id.desc()).all()


def revoke_api_token(db: Session, user_id: int, token_id: int) -> ApiToken:
    token = (
        db.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == user_id)
        .first()
    )
    if token is None:
        raise ValueError("API token not found")
    token.is_active = False
    db.add(
        AuditLog(
            user_id=user_id,
            action="api_token_revoked",
            before_value=f"token_id={token.id},name={token.name}",
            after_value="is_active=false",
        )
    )
    db.commit()
    db.refresh(token)
    return token
