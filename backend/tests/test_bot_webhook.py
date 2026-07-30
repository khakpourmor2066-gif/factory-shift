from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.connection import get_db
from app.main import app
from app.modules.bot_adapter import services as bot_services
from app.modules.bot_adapter.handlers import bot_handler
from app.modules.bot_adapter.services.webhook_service import format_bot_response
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

    def query(self, model):
        assert model is User
        return FakeQuery(self.user)


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def send_message(self, user_id: str, text: str, reply_markup=None) -> None:
        self.calls.append((user_id, text, reply_markup))


class FailingAdapter:
    def send_message(self, user_id: str, text: str, reply_markup=None) -> None:
        raise RuntimeError("provider failure")


def override_db(user):
    def _override():
        yield FakeSession(user)

    return _override


def test_bot_webhook_requires_secret():
    client = TestClient(app)

    response = client.post(
        "/bot/webhook",
        json={"messenger_user_id": "emp-1", "text": "منو"},
    )

    assert response.status_code == 401


def test_bot_webhook_sends_reply(monkeypatch):
    user = SimpleNamespace(id=1, role="EMPLOYEE", is_active=True, messenger_user_id="emp-1")
    fake_adapter = FakeAdapter()

    app.dependency_overrides[get_db] = override_db(user)
    monkeypatch.setattr(bot_services.webhook_service, "get_platform_adapter", lambda platform: fake_adapter)
    client = TestClient(app)

    try:
        response = client.post(
            "/bot/webhook",
            headers={"X-Bot-Secret": settings.bot_webhook_secret},
            json={"messenger_user_id": "emp-1", "text": "منو"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["response"]["type"] == "menu"
    assert fake_adapter.calls == [
            (
                "emp-1",
                "منو",
                {
                        "inline_keyboard": [
                            [{"text": "برنامه من", "callback_data": "VIEW_MY_SHIFT"}],
                            [{"text": "ماه", "callback_data": "SELECT_MONTH"}],
                            [{"text": "راهنما", "callback_data": "HELP"}],
                            [{"text": "خروج از حساب", "callback_data": "LOGOUT_REQUEST"}],
                        ]
                    },
            )
        ]


def test_bot_webhook_returns_bad_gateway_when_delivery_fails(monkeypatch):
    user = SimpleNamespace(id=1, role="EMPLOYEE", is_active=True, messenger_user_id="emp-1")

    app.dependency_overrides[get_db] = override_db(user)
    monkeypatch.setattr(
        bot_services.webhook_service,
        "get_platform_adapter",
        lambda platform: FailingAdapter(),
    )
    client = TestClient(app)

    try:
        response = client.post(
            "/bot/webhook",
            headers={"X-Bot-Secret": settings.bot_webhook_secret},
            json={"messenger_user_id": "emp-1", "text": "منو"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "messaging platform delivery failed"}


def test_format_supervisor_schedule_lists_employees():
    response = {
        "type": "supervisor_schedule",
        "data": {
            "date": "2026-07-26",
            "employees": [{"full_name": "Ali Reza", "status": "day"}],
        },
    }

    text = format_bot_response(response)

    assert "2026-07-26 · 1 نفر" in text
    assert "Ali Reza" in text
    assert "روز" in text


def test_supervisor_schedule_includes_status_summary():
    response = {
        "type": "supervisor_schedule",
        "data": {
            "date": "2026-07-26",
            "employees": [
                {"full_name": "Ali Reza", "status": "DAY"},
                {"full_name": "Sara Ahmadi", "status": "NIGHT"},
                {"full_name": "Reza Karimi", "status": "NIGHT"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "خلاصه: روز: 1" in text
    assert "شب: 2" in text


def test_supervisor_empty_schedule_suggests_date_selection():
    response = {
        "type": "supervisor_schedule",
        "data": {
            "date": "2026-07-26",
            "employees": [],
        },
    }

    text = format_bot_response(response)

    assert "برای 2026-07-26 برنامه‌ای ثبت نشده است." in text
    assert "از «تاریخ» روز دیگری را انتخاب کنید." in text


def test_supervisor_schedule_truncates_long_employee_list():
    response = {
        "type": "supervisor_schedule",
        "data": {
            "date": "2026-07-26",
            "employees": [
                {"full_name": "Person 1", "status": "DAY"},
                {"full_name": "Person 2", "status": "DAY"},
                {"full_name": "Person 3", "status": "DAY"},
                {"full_name": "Person 4", "status": "DAY"},
                {"full_name": "Person 5", "status": "DAY"},
                {"full_name": "Person 6", "status": "DAY"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "Person 1" in text
    assert "Person 5" in text
    assert "Person 6" not in text
    assert "+ 1 نفر دیگر" in text


def test_supervisor_schedule_show_more_button_is_added():
    response = {
        "type": "supervisor_schedule",
        "data": {
            "date": "2026-07-26",
            "employees": [
                {"full_name": "Person 1", "status": "DAY"},
                {"full_name": "Person 2", "status": "DAY"},
                {"full_name": "Person 3", "status": "DAY"},
                {"full_name": "Person 4", "status": "DAY"},
                {"full_name": "Person 5", "status": "DAY"},
                {"full_name": "Person 6", "status": "DAY"},
            ],
        },
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "نمایش بیشتر", "callback_data": "SHOW_MORE_SUPERVISOR:2026-07-26"}],
                [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
            ]
        },
    }

    text = format_bot_response(response)

    assert "Person 6" not in text


def test_supervisor_full_view_has_show_less_button():
    response = {
        "type": "supervisor_schedule",
        "detail_level": "full",
        "data": {
            "date": "2026-07-26",
            "employees": [
                {"full_name": "Person 1", "status": "DAY"},
            ],
        },
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "نمایش کمتر", "callback_data": "SHOW_LESS_SUPERVISOR:2026-07-26"}],
                [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
            ]
        },
    }

    text = format_bot_response(response)

    assert "جزئیات:" in text
    assert "Person 1" in text


def test_shift_status_is_localized():
    response = {
        "type": "employee_schedule",
        "data": {
            "employee_name": "Ali Worker",
            "days": [
                {"date": "2026-07-26", "status": "DAY"},
                {"date": "2026-07-27", "status": "NIGHT"},
                {"date": "2026-07-28", "status": "REST"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "روز" in text
    assert "شب" in text
    assert "استراحت" in text


def test_employee_schedule_includes_status_summary():
    response = {
        "type": "employee_schedule",
        "data": {
            "employee_name": "Ali Worker",
            "days": [
                {"date": "2026-07-26", "status": "DAY"},
                {"date": "2026-07-27", "status": "DAY"},
                {"date": "2026-07-28", "status": "NIGHT"},
                {"date": "2026-07-29", "status": "REST"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "خلاصه: روز: 2" in text
    assert "شب: 1" in text
    assert "استراحت: 1" in text


def test_employee_empty_schedule_suggests_month_selection():
    response = {
        "type": "employee_schedule",
        "data": {
            "employee_name": "Ali Worker",
            "days": [],
        },
    }

    text = format_bot_response(response)

    assert "برای این بازه برنامه‌ای ثبت نشده است." in text
    assert "از «ماه» بازه دیگری را انتخاب کنید." in text


def test_employee_full_view_includes_details_label():
    response = {
        "type": "employee_schedule",
        "detail_level": "full",
        "data": {
            "employee_name": "Ali Worker",
            "days": [
                {"date": "2026-07-26", "status": "DAY"},
                {"date": "2026-07-27", "status": "NIGHT"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "جزئیات:" in text
    assert "2026-07-26: روز" in text
    assert "2026-07-27: شب" in text


def test_supervisor_full_view_includes_details_label():
    response = {
        "type": "supervisor_schedule",
        "detail_level": "full",
        "data": {
            "date": "2026-07-26",
            "employees": [
                {"full_name": "Ali Reza", "status": "DAY"},
                {"full_name": "Sara Ahmadi", "status": "NIGHT"},
            ],
        },
    }

    text = format_bot_response(response)

    assert "جزئیات:" in text
    assert "Ali Reza: روز" in text
    assert "Sara Ahmadi: شب" in text


def test_supervisor_date_help_has_reply_keyboard():
    result = bot_handler.resolve_user_message(None, SimpleNamespace(role="SUPERVISOR"), "انتخاب تاریخ")

    assert result["type"] == "date_help"
    assert result["reply_markup"] == {
        "inline_keyboard": [
            [{"text": "امروز", "callback_data": "VIEW_DAY_TODAY"}],
            [{"text": "فردا", "callback_data": "VIEW_DAY_TOMORROW"}],
            [{"text": "پس‌فردا", "callback_data": "VIEW_DAY_AFTER_TOMORROW"}],
            [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
        ]
    }
