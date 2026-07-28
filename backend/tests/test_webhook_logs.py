from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.modules.users.model import User
from app.modules.webhook_logs.model import WebhookLog


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def all(self):
        return self.result if isinstance(self.result, list) else [self.result] if self.result else []

    def first(self):
        return self.result[0] if isinstance(self.result, list) else self.result


class FakeSession:
    def __init__(self, user, logs):
        self.user = user
        self.logs = logs

    def query(self, model):
        if model is User:
            return FakeQuery(self.user)
        if model is WebhookLog:
            return FakeQuery(self.logs)
        raise AssertionError(f"Unexpected model: {model}")


def override_db(session):
    def _override():
        yield session

    return _override


def test_webhook_logs_report_requires_privileged_role():
    session = FakeSession(SimpleNamespace(id=1, role="EMPLOYEE", is_active=True), [])
    app.dependency_overrides[get_db] = override_db(session)
    client = TestClient(app)

    try:
        response = client.get("/webhook-logs/report", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_webhook_logs_report_returns_counts():
    log = SimpleNamespace(
        id=1,
        platform="bale",
        messenger_user_id="999",
        direction="incoming",
        event_type="unknown_user",
        request_text="hello",
        response_status="unknown_user",
        response_text="reply",
        sent_status=True,
        created_at="2026-07-27T00:00:00Z",
    )
    session = FakeSession(SimpleNamespace(id=1, role="SUPERVISOR", is_active=True), [log])
    app.dependency_overrides[get_db] = override_db(session)
    client = TestClient(app)

    try:
        response = client.get("/webhook-logs/report", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["counts"]["incoming"] == 1
    assert response.json()["total"] == 1
