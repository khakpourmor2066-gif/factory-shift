from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.bot_adapter.handlers import bot_handler
from app.modules.bot_adapter.services.webhook_service import format_bot_response


def test_employee_schedule_message_is_detected(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        return {"employee_id": 1, "days": []}

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    result = bot_handler.resolve_user_message(None, user, "برنامه شیفت من")

    assert result["type"] == "employee_schedule"


def test_start_message_uses_welcome():
    user = SimpleNamespace(role="EMPLOYEE")

    result = bot_handler.resolve_user_message(None, user, "/start")

    assert result["type"] == "welcome"
    assert result["text"] == (
        "به ربات نمایش شیفت‌های کاری خوش آمدید.\n"
        "یکی از گزینه‌های زیر را انتخاب کنید."
    )
    assert "فعال‌سازی" not in format_bot_response(result)
    assert "درخواست" not in format_bot_response(result)
    assert result["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "VIEW_MY_SHIFT"


def test_short_employee_menu_label_is_detected(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        return {"employee_id": 1, "days": []}

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    result = bot_handler.resolve_user_message(None, user, "برنامه من")

    assert result["type"] == "employee_schedule"


def test_supervisor_daily_staff_message_is_detected(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        assert target_date == date.today()
        return {"employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "مشاهده افراد یک روز")

    assert result["type"] == "supervisor_schedule"


def test_supervisor_date_message_uses_requested_date(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        assert target_date == date(2026, 7, 26)
        return {"date": target_date, "employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ 2026-07-26")

    assert result["type"] == "supervisor_schedule"


def test_supervisor_date_message_accepts_persian_digits(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        assert target_date == date(2026, 7, 26)
        return {"date": target_date, "employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ ۲۰۲۶-۰۷-۲۶")

    assert result["type"] == "supervisor_schedule"


def test_supervisor_date_message_accepts_common_separators(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")
    captured_dates = []

    def fake_get_supervisor_schedule(db, current_user, target_date):
        captured_dates.append(target_date)
        return {"date": target_date, "employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    slash_result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ 2026/07/26")
    dot_result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ 2026.07.27")

    assert slash_result["type"] == "supervisor_schedule"
    assert dot_result["type"] == "supervisor_schedule"
    assert captured_dates == [date(2026, 7, 26), date(2026, 7, 27)]


def test_invalid_date_text_returns_date_help(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        raise AssertionError("invalid date should not load a schedule")

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ 2026-13-40")

    assert result["type"] == "date_help"
    assert result["text"] == "تاریخ معتبر نیست. نمونه درست: 2026-07-26"


def test_supervisor_direct_date_loads_schedule(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        assert target_date == date(2026, 7, 26)
        return {"date": target_date, "employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "2026-07-26")

    assert result["type"] == "supervisor_schedule"


def test_direct_invalid_date_returns_date_help(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        raise AssertionError("invalid direct date should not load a schedule")

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    result = bot_handler.resolve_user_message(None, user, "2026-13-40")

    assert result["type"] == "date_help"
    assert result["text"] == "تاریخ معتبر نیست. نمونه درست: 2026-07-26"


def test_date_help_message_is_detected():
    user = SimpleNamespace(role="SUPERVISOR")

    result = bot_handler.resolve_user_message(None, user, "انتخاب تاریخ")

    assert result["type"] == "date_help"
    assert result["text"] == "تاریخ را انتخاب کنید یا YYYY-MM-DD بنویسید."


def test_month_help_message_is_detected():
    user = SimpleNamespace(role="EMPLOYEE")

    result = bot_handler.resolve_user_message(None, user, "انتخاب ماه")

    assert result["type"] == "month_help"
    assert result["text"] == "ماه را انتخاب کنید."
    assert result["reply_markup"] == {
        "inline_keyboard": [
            [{"text": "ماه قبل", "callback_data": "VIEW_MONTH_PREVIOUS"}],
            [{"text": "ماه جاری", "callback_data": "VIEW_MONTH_CURRENT"}],
            [{"text": "ماه بعد", "callback_data": "VIEW_MONTH_NEXT"}],
            [{"text": "بازگشت", "callback_data": "BACK_MENU"}],
        ]
    }


def test_month_callback_loads_employee_month(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        assert from_date.day == 1
        assert to_date >= from_date
        return {"employee_id": 1, "employee_name": "Ali Worker", "days": []}

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    result = bot_handler.resolve_user_message(None, user, "VIEW_MONTH_CURRENT")

    assert result["type"] == "employee_schedule"


def test_month_text_commands_load_employee_month(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")
    captured_ranges = []

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        captured_ranges.append((from_date, to_date))
        return {"employee_id": 1, "employee_name": "Ali Worker", "days": []}

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    current_result = bot_handler.resolve_user_message(None, user, "ماه جاری")
    next_result = bot_handler.resolve_user_message(None, user, "ماه بعد")
    previous_result = bot_handler.resolve_user_message(None, user, "ماه قبل")

    assert current_result["type"] == "employee_schedule"
    assert next_result["type"] == "employee_schedule"
    assert previous_result["type"] == "employee_schedule"
    assert len(captured_ranges) == 3


def test_callback_commands_are_detected(monkeypatch):
    user = SimpleNamespace(role="SUPERVISOR")

    def fake_get_supervisor_schedule(db, current_user, target_date):
        return {"date": target_date, "employees": []}

    monkeypatch.setattr(bot_handler, "get_supervisor_schedule", fake_get_supervisor_schedule)

    assert bot_handler.resolve_user_message(None, user, "VIEW_DAY_STAFF")["type"] == "supervisor_schedule"
    assert bot_handler.resolve_user_message(None, user, "SELECT_DATE")["type"] == "date_help"
    assert bot_handler.resolve_user_message(None, user, "VIEW_DAY_TOMORROW")["type"] == "supervisor_schedule"
    assert bot_handler.resolve_user_message(None, user, "HELP")["type"] == "help"
    assert bot_handler.resolve_user_message(None, user, "MENU")["type"] == "menu"
    assert bot_handler.resolve_user_message(None, user, "BACK_MENU")["type"] == "menu"


def test_admin_operations_command_is_detected():
    user = SimpleNamespace(role="ADMIN")

    assert bot_handler.resolve_user_message(None, user, "عملیات")["type"] == "operations_menu"


def test_common_slash_commands_are_detected():
    user = SimpleNamespace(role="EMPLOYEE")

    assert bot_handler.resolve_user_message(None, user, "/menu")["type"] == "menu"
    assert bot_handler.resolve_user_message(None, user, "/help")["type"] == "help"


def test_help_message_is_role_specific():
    employee = SimpleNamespace(role="EMPLOYEE")
    supervisor = SimpleNamespace(role="SUPERVISOR")

    employee_result = bot_handler.resolve_user_message(None, employee, "راهنما")
    supervisor_result = bot_handler.resolve_user_message(None, supervisor, "راهنما")

    assert employee_result["text"] == "برای دیدن برنامه خود، «برنامه من» را بزنید."
    assert supervisor_result["text"] == "برای مشاهده افراد روز، «افراد روز» را بزنید."


def test_identity_missing_message_is_short_and_step_based():
    response = {"type": "identity_missing"}

    text = format_bot_response(response)

    assert "ابتدا شماره تلفن همراه" in text
    assert "کد کارمندی" in text


def test_contact_received_message_is_step_based():
    response = {"type": "contact_received"}

    text = format_bot_response(response)

    assert "شماره تلفن همراه دریافت شد." in text
    assert "اکنون، شماره کارمندی خود را ارسال کنید." in text


def test_employee_cannot_view_supervisor_schedule():
    user = SimpleNamespace(role="EMPLOYEE")

    with pytest.raises(HTTPException) as error:
        bot_handler.resolve_user_message(None, user, "مشاهده افراد یک روز")

    assert error.value.status_code == 403


def test_unknown_message_uses_help_reply():
    user = SimpleNamespace(role="EMPLOYEE")

    result = bot_handler.resolve_user_message(None, user, "سلام")

    assert result["type"] == "help"
    assert result["reply_markup"] == {"inline_keyboard": [[{"text": "بازگشت", "callback_data": "BACK_MENU"}]]}


def test_show_more_employee_command_loads_full_schedule(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        return {"employee_id": 1, "employee_name": "Ali Worker", "days": [{"date": "2026-07-26", "status": "DAY"}]}

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    result = bot_handler.resolve_user_message(None, user, "SHOW_MORE_EMPLOYEE:2026-07-01:2026-07-31")

    assert result["type"] == "employee_schedule"
    assert result["detail_level"] == "full"


def test_show_less_employee_command_restores_summary(monkeypatch):
    user = SimpleNamespace(role="EMPLOYEE")

    def fake_get_my_schedule(db, current_user, from_date, to_date):
        return {
            "employee_id": 1,
            "employee_name": "Ali Worker",
            "days": [
                {"date": "2026-07-01", "status": "DAY"},
                {"date": "2026-07-02", "status": "NIGHT"},
            ],
        }

    monkeypatch.setattr(bot_handler, "get_my_schedule", fake_get_my_schedule)

    result = bot_handler.resolve_user_message(None, user, "SHOW_LESS_EMPLOYEE:2026-07-01:2026-07-31")

    assert result["type"] == "employee_schedule"
    assert result["detail_level"] == "summary"
