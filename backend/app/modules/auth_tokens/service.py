import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.modules.auth_tokens.model import ApiToken, WebLoginTicket
from app.modules.change_management.model import AuditLog
from app.modules.users.model import User


WEB_SESSION_COOKIE = "factory_shift_session"
WEB_LOGIN_TICKET_MINUTES = 5
WEB_SESSION_HOURS = 8


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


def create_web_login_ticket(
    db: Session,
    user_id: int,
    *,
    lifetime_minutes: int = WEB_LOGIN_TICKET_MINUTES,
) -> tuple[WebLoginTicket, str]:
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None or user.role not in {"HR", "ADMIN"}:
        raise ValueError("HR or Admin user is required")

    now = datetime.now(UTC)
    pending_tickets = (
        db.query(WebLoginTicket)
        .filter(
            WebLoginTicket.user_id == user_id,
            WebLoginTicket.consumed_at.is_(None),
        )
        .all()
    )
    for ticket in pending_tickets:
        ticket.consumed_at = now

    raw_ticket = secrets.token_urlsafe(32)
    ticket = WebLoginTicket(
        user_id=user_id,
        token_hash=hash_token(raw_ticket),
        expires_at=now + timedelta(minutes=lifetime_minutes),
    )
    db.add(ticket)
    db.add(
        AuditLog(
            user_id=user_id,
            action="web_login_ticket_created",
            after_value=f"expires_at={ticket.expires_at.isoformat()}",
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket, raw_ticket


def consume_web_login_ticket(
    db: Session,
    raw_ticket: str,
) -> tuple[User, ApiToken, str]:
    now = datetime.now(UTC)
    ticket = (
        db.query(WebLoginTicket)
        .filter(WebLoginTicket.token_hash == hash_token(raw_ticket))
        .with_for_update()
        .first()
    )
    if ticket is None or ticket.consumed_at is not None:
        raise ValueError("invalid or consumed web login link")

    expires_at = ticket.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        ticket.consumed_at = now
        db.commit()
        raise ValueError("expired web login link")

    user = db.query(User).filter(User.id == ticket.user_id, User.is_active.is_(True)).first()
    if user is None or user.role not in {"HR", "ADMIN"}:
        ticket.consumed_at = now
        db.commit()
        raise ValueError("web access is no longer allowed")

    ticket.consumed_at = now
    active_sessions = (
        db.query(ApiToken)
        .filter(
            ApiToken.user_id == user.id,
            ApiToken.name == "bale-web-session",
            ApiToken.is_active.is_(True),
        )
        .all()
    )
    for token in active_sessions:
        token.is_active = False

    session_token, raw_session_token = create_api_token(
        db,
        user_id=user.id,
        name="bale-web-session",
        expires_at=now + timedelta(hours=WEB_SESSION_HOURS),
    )
    return user, session_token, raw_session_token


def revoke_web_session(db: Session, raw_session_token: str) -> None:
    token = (
        db.query(ApiToken)
        .filter(
            ApiToken.token_hash == hash_token(raw_session_token),
            ApiToken.name == "bale-web-session",
            ApiToken.is_active.is_(True),
        )
        .first()
    )
    if token is None:
        return
    token.is_active = False
    db.add(
        AuditLog(
            user_id=token.user_id,
            action="web_session_revoked",
            before_value=f"token_id={token.id}",
            after_value="is_active=false",
        )
    )
    db.commit()


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
