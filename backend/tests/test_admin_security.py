from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.main import app
from app.modules.access.dependencies import get_current_user


class FakeSession:
    pass


def override_db():
    def _override():
        yield FakeSession()

    return _override


def test_employee_cannot_list_users():
    app.dependency_overrides[get_db] = override_db()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="EMPLOYEE", is_active=True)
    client = TestClient(app)

    try:
        response = client.get("/users")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_employee_cannot_list_employees():
    app.dependency_overrides[get_db] = override_db()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="EMPLOYEE", is_active=True)
    client = TestClient(app)

    try:
        response = client.get("/employees")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
