from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.modules.access_requests.model import AccessRequest
from app.modules.users.model import User


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def limit(self, *args):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.result if isinstance(self.result, list) else [self.result] if self.result else []


class FakeSession:
    def __init__(self, user, access_requests=None):
        self.user = user
        self.access_requests = access_requests or []

    def query(self, model):
        if model is User:
            return FakeQuery(self.user)
        if model is AccessRequest:
            return FakeQuery(self.access_requests)
        raise AssertionError(f"Unexpected model: {model}")


def override_db(session):
    def _override():
        yield session

    return _override


def test_pending_access_requests_requires_supervisor():
    session = FakeSession(SimpleNamespace(id=1, role="EMPLOYEE", is_active=True))
    app.dependency_overrides[get_db] = override_db(session)
    client = TestClient(app)

    try:
        response = client.get("/access-requests/pending", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_pending_access_requests_returns_rows_for_supervisor():
    request_row = SimpleNamespace(
        id=1,
        platform="bale",
        messenger_user_id="999",
        latest_text="منو",
        status="pending",
        request_count=1,
        created_at="2026-07-27T00:00:00Z",
        updated_at="2026-07-27T00:00:00Z",
    )
    session = FakeSession(SimpleNamespace(id=1, role="SUPERVISOR", is_active=True), [request_row])
    app.dependency_overrides[get_db] = override_db(session)
    client = TestClient(app)

    try:
        response = client.get("/access-requests/pending", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["messenger_user_id"] == "999"


def test_access_request_report_returns_counts():
    request_row = SimpleNamespace(
        id=1,
        platform="bale",
        messenger_user_id="999",
        latest_text="منو",
        status="pending",
        request_count=1,
        created_at="2026-07-27T00:00:00Z",
        updated_at="2026-07-27T00:00:00Z",
    )
    session = FakeSession(SimpleNamespace(id=1, role="SUPERVISOR", is_active=True), [request_row])
    app.dependency_overrides[get_db] = override_db(session)
    client = TestClient(app)

    try:
        response = client.get("/access-requests/report", headers={"X-User-Id": "1"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["counts"]["pending"] == 1
    assert response.json()["total"] == 1
