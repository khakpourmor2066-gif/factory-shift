from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.bot_adapter.handlers import bot_handler
from app.modules.bot_adapter.services.webhook_service import format_bot_response


def test_hr_can_view_pending_access_requests(monkeypatch):
    user = SimpleNamespace(role="HR")
    request = {
        "id": 7,
        "messenger_user_id": "999",
        "request_count": 2,
        "mobile": "09120000002",
        "personnel_code": "SUP-001",
        "employee_name": "Sara Mohammadi",
        "employee_role": "SUPERVISOR",
        "registered_mobile": "09120000002",
        "registered_personnel_code": "SUP-001",
        "match_status": "matched",
        "match_label": "شماره همراه و کد کارمندی معتبر است ✅",
        "can_approve": True,
    }

    monkeypatch.setattr(
        bot_handler,
        "list_pending_access_request_reviews",
        lambda db, limit=5: [request],
    )

    result = bot_handler.resolve_user_message(None, user, "درخواست‌ها")
    text = format_bot_response(result)

    assert result["type"] == "access_requests"
    assert "#7" in text
    assert "09120000002" in text
    assert "SUP-001" in text
    assert "Sara Mohammadi" in text
    assert "SUPERVISOR" in text
    assert "معتبر است" in text
    assert result["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "APPROVE_ACCESS:7"
    assert result["reply_markup"]["inline_keyboard"][0][1]["callback_data"] == "REJECT_ACCESS:7"


def test_invalid_request_only_has_reject_button(monkeypatch):
    user = SimpleNamespace(role="HR")
    request = {
        "id": 3,
        "messenger_user_id": "9003",
        "request_count": 1,
        "mobile": "09120009999",
        "personnel_code": "EMP-999",
        "employee_name": None,
        "employee_role": None,
        "registered_mobile": None,
        "registered_personnel_code": None,
        "match_status": "employee_not_found",
        "match_label": "کارمند در فهرست منابع انسانی پیدا نشد ❌",
        "can_approve": False,
    }
    monkeypatch.setattr(
        bot_handler,
        "list_pending_access_request_reviews",
        lambda db, limit=5: [request],
    )

    result = bot_handler.resolve_user_message(None, user, "VIEW_ACCESS_REQUESTS")
    buttons = result["reply_markup"]["inline_keyboard"]

    assert buttons[0] == [{"text": "رد 3", "callback_data": "REJECT_ACCESS:3"}]
    assert "APPROVE_ACCESS:3" not in str(buttons)


def test_hr_can_approve_access_request_from_bot(monkeypatch):
    user = SimpleNamespace(role="HR")
    request = SimpleNamespace(id=7)
    captured_audit = []

    monkeypatch.setattr(bot_handler, "approve_access_request", lambda db, request_id: ("approved", request))
    monkeypatch.setattr(bot_handler, "notify_access_request_result", lambda access_request, status: True)
    monkeypatch.setattr(bot_handler, "create_audit_log", lambda db, payload: captured_audit.append(payload))

    result = bot_handler.resolve_user_message(None, user, "APPROVE_ACCESS:7")
    text = format_bot_response(result)

    assert result["type"] == "access_request_review"
    assert result["data"]["notification_sent"] is True
    assert "تایید و کاربر فعال شد" in text
    assert captured_audit[0].action == "access_request_approved_via_bot"


def test_hr_can_reject_access_request_from_bot(monkeypatch):
    user = SimpleNamespace(role="HR")
    request = SimpleNamespace(id=7)
    captured_audit = []

    monkeypatch.setattr(bot_handler, "reject_access_request", lambda db, request_id: ("rejected", request))
    monkeypatch.setattr(bot_handler, "notify_access_request_result", lambda access_request, status: True)
    monkeypatch.setattr(bot_handler, "create_audit_log", lambda db, payload: captured_audit.append(payload))

    result = bot_handler.resolve_user_message(None, user, "REJECT_ACCESS:7")
    text = format_bot_response(result)

    assert result["type"] == "access_request_review"
    assert result["data"]["notification_sent"] is True
    assert "رد شد" in text
    assert captured_audit[0].action == "access_request_rejected_via_bot"


def test_employee_cannot_view_access_requests():
    user = SimpleNamespace(role="EMPLOYEE")

    try:
        bot_handler.resolve_user_message(None, user, "درخواست‌ها")
    except Exception as error:
        assert getattr(error, "status_code", None) == 403
    else:
        raise AssertionError("employee should not view access requests")


def test_admin_can_open_operations_menu():
    user = SimpleNamespace(role="ADMIN")

    result = bot_handler.resolve_user_message(None, user, "عملیات")
    text = format_bot_response(result)

    assert result["type"] == "operations_menu"
    assert "بخش عملیات آماده است." in text
    assert result["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "VIEW_ACCESS_REQUESTS"


def test_admin_can_view_access_request_report(monkeypatch):
    user = SimpleNamespace(role="ADMIN")
    report = {"counts": {"pending": 2, "approved": 1, "rejected": 1}, "total": 4, "latest": []}

    monkeypatch.setattr(bot_handler, "get_access_request_report", lambda db: report)

    result = bot_handler.resolve_user_message(None, user, "VIEW_ACCESS_REQUEST_REPORT")
    text = format_bot_response(result)

    assert result["type"] == "access_request_report"
    assert "کل درخواست‌ها: 4" in text
    assert "در انتظار: 2" in text


def test_admin_can_view_webhook_log_report(monkeypatch):
    user = SimpleNamespace(role="ADMIN")
    report = {"counts": {"incoming": 3, "outgoing": 5, "sent": 7, "failed": 1}, "total": 8, "latest": []}

    monkeypatch.setattr(bot_handler, "get_webhook_log_report", lambda db: report)

    result = bot_handler.resolve_user_message(None, user, "VIEW_WEBHOOK_LOG_REPORT")
    text = format_bot_response(result)

    assert result["type"] == "webhook_log_report"
    assert "کل لاگ‌ها: 8" in text
    assert "ارسال موفق: 7" in text


@pytest.mark.parametrize(
    "command",
    [
        "درخواست‌ها",
        "عملیات",
        "VIEW_ACCESS_REQUEST_REPORT",
        "VIEW_WEBHOOK_LOG_REPORT",
        "APPROVE_ACCESS:7",
        "REJECT_ACCESS:7",
    ],
)
def test_supervisor_cannot_use_management_commands(command):
    user = SimpleNamespace(role="SUPERVISOR")

    with pytest.raises(HTTPException) as error:
        bot_handler.resolve_user_message(None, user, command)

    assert error.value.status_code == 403
