from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.connection import get_db
from app.main import app
from app.modules.bot_adapter.services.bale_webhook_service import extract_bale_incoming_message
from app.modules.access_requests.model import AccessRequest
from app.modules.users.model import User


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *args):
        return self

    def first(self):
        return self.user


class FakeSession:
    def __init__(self, user):
        self.user = user
        self.created_requests = []
        self.access_request = None

    def query(self, model):
        if model is User:
            return FakeQuery(self.user)
        if model is AccessRequest:
            return FakeAccessRequestQuery(self.access_request)
        raise AssertionError(f"Unexpected model: {model}")

    def add(self, obj):
        self.created_requests.append(obj)
        self.access_request = obj

    def commit(self):
        if self.access_request and self.access_request.id is None:
            self.access_request.id = 101

    def refresh(self, obj):
        return None


class FakeAccessRequestQuery:
    def __init__(self, access_request):
        self.access_request = access_request

    def filter(self, *args):
        return self

    def first(self):
        return self.access_request


def override_db(user):
    def _override():
        yield FakeSession(user)

    return _override


def test_extract_bale_message_from_message_chat():
    payload = {"message": {"chat": {"id": 132}, "text": "منو"}}

    messenger_user_id, text = extract_bale_incoming_message(payload)

    assert messenger_user_id == "132"
    assert text == "منو"


def test_extract_bale_contact_as_activation_text():
    payload = {
        "message": {
            "chat": {"id": 132},
            "contact": {"phone_number": "+989120000002"},
        }
    }

    messenger_user_id, text = extract_bale_incoming_message(payload)

    assert messenger_user_id == "132"
    assert text == "CONTACT_MOBILE:09120000002"


def test_bale_webhook_endpoint_accepts_signed_path(monkeypatch):
    user = SimpleNamespace(id=1, role="EMPLOYEE", is_active=True, messenger_user_id="132")
    app.dependency_overrides[get_db] = override_db(user)
    client = TestClient(app)

    try:
        response = client.post(
            f"/bot/bale/webhook/{settings.bot_webhook_secret}",
            json={"message": {"chat": {"id": 132}, "text": "منو"}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_bale_webhook_unknown_user_creates_access_request(monkeypatch):
    session = FakeSession(None)

    def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)

    try:
        response = client.post(
            f"/bot/bale/webhook/{settings.bot_webhook_secret}",
            json={"message": {"chat": {"id": 999}, "text": "منو"}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unknown_user"
    assert body["access_request_id"] == 101
    assert session.created_requests[0].messenger_user_id == "999"
    assert session.created_requests[0].latest_text == "منو"
