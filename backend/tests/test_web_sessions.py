from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.main import app
from app.modules.auth_tokens.model import ApiToken, WebLoginTicket
from app.modules.auth_tokens.service import WEB_SESSION_COOKIE, create_web_login_ticket
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
    user = User(mobile="09120000600", role="HR", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app, base_url="https://testserver"), db, user


def close_client(db):
    app.dependency_overrides.clear()
    db.close()


def test_one_time_link_creates_secure_cookie_and_authenticates_dashboard():
    client, db, user = create_client()
    try:
        _, raw_ticket = create_web_login_ticket(db, user.id)

        landing_response = client.get(
            f"/admin/session/{raw_ticket}",
            follow_redirects=False,
        )
        assert landing_response.status_code == 200
        assert "ورود به پیشخوان مدیریت" in landing_response.text
        assert db.query(WebLoginTicket).one().consumed_at is None

        login_response = client.post(
            f"/admin/session/{raw_ticket}/confirm",
            follow_redirects=False,
        )
        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/admin/dashboard"
        cookie_header = login_response.headers["set-cookie"]
        assert f"{WEB_SESSION_COOKIE}=" in cookie_header
        assert "HttpOnly" in cookie_header
        assert "Secure" in cookie_header
        assert "SameSite=strict" in cookie_header

        dashboard_response = client.get("/admin/dashboard")
        options_response = client.get("/schedule-generation/options")
        assert dashboard_response.status_code == 200
        assert options_response.status_code == 200
        assert db.query(WebLoginTicket).one().consumed_at is not None
        assert db.query(ApiToken).filter(ApiToken.name == "bale-web-session").one().is_active is True
    finally:
        close_client(db)


def test_get_can_be_repeated_but_confirmation_cannot_be_consumed_twice():
    client, db, user = create_client()
    try:
        _, raw_ticket = create_web_login_ticket(db, user.id)
        first_landing = client.get(f"/admin/session/{raw_ticket}", follow_redirects=False)
        second_landing = client.get(f"/admin/session/{raw_ticket}", follow_redirects=False)
        first_response = client.post(
            f"/admin/session/{raw_ticket}/confirm",
            follow_redirects=False,
        )
        second_response = client.post(
            f"/admin/session/{raw_ticket}/confirm",
            follow_redirects=False,
        )

        assert first_landing.status_code == 200
        assert second_landing.status_code == 200
        assert first_response.status_code == 303
        assert second_response.status_code == 401
        assert "قبلاً استفاده شده" in second_response.text
    finally:
        close_client(db)


def test_web_login_rejects_external_redirect_target():
    client, db, user = create_client()
    try:
        _, raw_ticket = create_web_login_ticket(db, user.id)
        response = client.post(
            f"/admin/session/{raw_ticket}/confirm?next=https://evil.example",
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/dashboard"
    finally:
        close_client(db)


def test_expired_web_login_link_is_rejected():
    client, db, user = create_client()
    try:
        ticket, raw_ticket = create_web_login_ticket(db, user.id)
        ticket.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

        response = client.get(f"/admin/session/{raw_ticket}", follow_redirects=False)

        assert response.status_code == 401
        assert "مهلت این لینک پایان یافته" in response.text
        assert db.query(ApiToken).filter(ApiToken.name == "bale-web-session").count() == 0
    finally:
        close_client(db)


def test_web_logout_revokes_session_and_clears_cookie():
    client, db, user = create_client()
    try:
        _, raw_ticket = create_web_login_ticket(db, user.id)
        client.post(f"/admin/session/{raw_ticket}/confirm", follow_redirects=False)

        logout_response = client.post("/admin/session/logout", follow_redirects=False)
        dashboard_response = client.get("/admin/dashboard")

        assert logout_response.status_code == 200
        assert "خارج شدید" in logout_response.text
        assert dashboard_response.status_code == 401
        assert db.query(ApiToken).filter(ApiToken.name == "bale-web-session").one().is_active is False
    finally:
        close_client(db)
from datetime import UTC, datetime, timedelta
