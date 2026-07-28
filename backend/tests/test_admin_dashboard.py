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
