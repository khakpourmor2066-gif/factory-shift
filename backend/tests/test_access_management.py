from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.modules.access.dependencies import get_current_user
from app.modules.access_requests.model import AccessRequest
from app.modules.access_requests import router as access_requests_router
from app.modules.users.model import User


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result

    def all(self):
        return self.result if isinstance(self.result, list) else [self.result] if self.result else []


class FakeSession:
    def __init__(self, user=None, users=None, access_requests=None):
        self.user = user
        self.users = users or []
        self.access_requests = access_requests or []
        self.added_objects = []

    def query(self, model):
        if model is User:
            return FakeQuery(self.users[0] if self.users else self.user)
        if model is AccessRequest:
            return FakeQuery(self.access_requests)
        raise AssertionError(f"Unexpected model: {model}")

    def commit(self):
        return None

    def add(self, obj):
        self.added_objects.append(obj)

    def refresh(self, obj):
        return None


def override_db(session):
    def _override():
        yield session

    return _override


def test_supervisor_can_update_user_role():
    supervisor = SimpleNamespace(id=1, role="SUPERVISOR", is_active=True)
    target_user = SimpleNamespace(id=2, role="EMPLOYEE", is_active=True, mobile="0912", messenger_user_id="222")
    session = FakeSession(user=target_user)
    app.dependency_overrides[get_db] = override_db(session)
    app.dependency_overrides[get_current_user] = lambda: supervisor
    client = TestClient(app)

    try:
        response = client.patch("/users/2/role", json={"role": "SUPERVISOR"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "SUPERVISOR"


def test_hr_can_update_access_request_status(monkeypatch):
    hr_user = SimpleNamespace(id=1, role="HR", is_active=True)
    access_request = SimpleNamespace(
        id=7,
        platform="bale",
        messenger_user_id="999",
        latest_text="منو",
        status="pending",
        request_count=1,
        created_at="2026-07-27T00:00:00Z",
        updated_at="2026-07-27T00:00:00Z",
    )
    session = FakeSession(access_requests=[access_request])
    captured_audit = []

    def approve_request(db, request_id):
        access_request.status = "approved"
        return "approved", access_request

    monkeypatch.setattr(access_requests_router, "notify_access_request_result", lambda updated_request, status_value: True)
    monkeypatch.setattr(
        access_requests_router,
        "approve_access_request",
        approve_request,
    )
    monkeypatch.setattr(
        access_requests_router,
        "create_audit_log",
        lambda db, payload: captured_audit.append(payload),
    )
    app.dependency_overrides[get_db] = override_db(session)
    app.dependency_overrides[get_current_user] = lambda: hr_user
    client = TestClient(app)

    try:
        response = client.patch("/access-requests/7/status", json={"status": "approved"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert captured_audit
    assert captured_audit[0].action == "access_request_status_updated"
    assert captured_audit[0].before_value == "pending"
    assert captured_audit[0].after_value == "approved"


def test_supervisor_cannot_update_access_request_status():
    supervisor = SimpleNamespace(id=1, role="SUPERVISOR", is_active=True)
    session = FakeSession()
    app.dependency_overrides[get_db] = override_db(session)
    app.dependency_overrides[get_current_user] = lambda: supervisor
    client = TestClient(app)

    try:
        response = client.patch("/access-requests/7/status", json={"status": "approved"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_employee_cannot_update_access_request_status():
    employee = SimpleNamespace(id=1, role="EMPLOYEE", is_active=True)
    session = FakeSession()
    app.dependency_overrides[get_db] = override_db(session)
    app.dependency_overrides[get_current_user] = lambda: employee
    client = TestClient(app)

    try:
        response = client.patch("/access-requests/7/status", json={"status": "approved"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
