from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.modules.access_requests.model import AccessRequest
from app.modules.users.model import User
from app.modules.webhook_logs.model import WebhookLog


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.result if isinstance(self.result, list) else [self.result] if self.result else []


class FakeSession:
    def __init__(self, user):
        self.user = user

    def query(self, model):
        if model is User:
            return FakeQuery(self.user)
        if model in {AccessRequest, WebhookLog}:
            return FakeQuery([])
        return FakeQuery(None)


def override_db(user):
    def _override():
        yield FakeSession(user)

    return _override


def test_admin_dashboard_requires_privileged_role():
    app.dependency_overrides[get_db] = override_db(SimpleNamespace(id=1, role="EMPLOYEE", is_active=True))
    client = TestClient(app)

    try:
        response = client.get("/admin/dashboard", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_dashboard_returns_html_for_supervisor():
    app.dependency_overrides[get_db] = override_db(SimpleNamespace(id=1, role="SUPERVISOR", is_active=True))
    client = TestClient(app)

    try:
        response = client.get("/admin/dashboard", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "داشبورد مدیریتی" in response.text
    assert "/admin/schedule-generator" not in response.text


def test_admin_dashboard_shows_schedule_generator_for_hr():
    app.dependency_overrides[get_db] = override_db(SimpleNamespace(id=1, role="HR", is_active=True))
    client = TestClient(app)

    try:
        response = client.get("/admin/dashboard", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "/admin/schedule-generator" in response.text


def test_import_dashboard_is_static_and_uses_bearer_api_calls():
    client = TestClient(app)

    response = client.get("/admin/imports")

    assert response.status_code == 200
    assert "ورود کارکنان و برنامه شیفت" in response.text
    assert "Authorization" in response.text
    assert "Bearer Token دستی (اختیاری)" in response.text
    assert "توکن و فایل الزامی است" not in response.text
    assert "/imports/${typeInput.value}/preview" in response.text
    assert response.headers["Cache-Control"] == "no-store"
