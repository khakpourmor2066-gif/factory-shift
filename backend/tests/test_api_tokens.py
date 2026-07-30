from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.core.config import settings
from app.main import app
from app.modules.auth_tokens.model import ApiToken
from app.modules.auth_tokens.service import authenticate_api_token, create_temporary_web_token
from app.modules.users.model import User


def create_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    user = User(mobile="09120000500", role="HR", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db, user


def close_client(db):
    app.dependency_overrides.clear()
    db.close()


def test_user_can_create_use_list_and_revoke_api_token():
    client, db, user = create_client()
    try:
        created = client.post(
            "/auth/tokens",
            headers={"X-User-Id": str(user.id)},
            json={"name": "automation"},
        )
        assert created.status_code == 200
        raw_token = created.json()["token"]
        token_id = created.json()["id"]
        assert raw_token
        assert db.query(ApiToken).one().token_hash != raw_token

        authenticated = client.get(
            "/auth/tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert authenticated.status_code == 200
        assert authenticated.json()[0]["last_used_at"] is not None

        revoked = client.delete(
            f"/auth/tokens/{token_id}",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert revoked.status_code == 200
        assert revoked.json()["is_active"] is False

        denied = client.get(
            "/auth/tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert denied.status_code == 401
    finally:
        close_client(db)


def test_expired_and_malformed_tokens_are_rejected():
    client, db, user = create_client()
    try:
        created = client.post(
            "/auth/tokens",
            headers={"X-User-Id": str(user.id)},
            json={
                "name": "expired",
                "expires_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            },
        )
        raw_token = created.json()["token"]
        token = db.query(ApiToken).filter(ApiToken.id == created.json()["id"]).one()
        token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

        expired = client.get(
            "/auth/tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        malformed = client.get("/auth/tokens", headers={"Authorization": "invalid"})
        assert expired.status_code == 401
        assert malformed.status_code == 401
    finally:
        close_client(db)


def test_legacy_header_can_be_disabled_after_bootstrap():
    client, db, user = create_client()
    original_setting = settings.allow_legacy_user_header
    try:
        created = client.post(
            "/auth/tokens",
            headers={"X-User-Id": str(user.id)},
            json={"name": "production"},
        )
        raw_token = created.json()["token"]
        settings.allow_legacy_user_header = False

        legacy = client.get("/auth/tokens", headers={"X-User-Id": str(user.id)})
        bearer = client.get(
            "/auth/tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert legacy.status_code == 401
        assert bearer.status_code == 200
    finally:
        settings.allow_legacy_user_header = original_setting
        close_client(db)


def test_temporary_web_token_replaces_previous_active_token():
    client, db, user = create_client()
    try:
        first_token, first_raw_token = create_temporary_web_token(db, user.id)
        second_token, second_raw_token = create_temporary_web_token(db, user.id)

        db.refresh(first_token)
        assert first_token.is_active is False
        assert second_token.is_active is True
        assert authenticate_api_token(db, first_raw_token) is None
        assert authenticate_api_token(db, second_raw_token).id == second_token.id
    finally:
        close_client(db)
