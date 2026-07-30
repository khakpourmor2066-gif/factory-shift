from app.modules.access.permissions import (
    can_generate_schedule,
    can_view_own_schedule,
    can_view_supervisor_schedule,
)


def test_employee_permissions():
    assert can_view_own_schedule("EMPLOYEE") is True
    assert can_view_supervisor_schedule("EMPLOYEE") is False
    assert can_generate_schedule("EMPLOYEE") is False


def test_supervisor_permissions():
    assert can_view_supervisor_schedule("SUPERVISOR") is True
    assert can_generate_schedule("SUPERVISOR") is False


def test_schedule_generation_permissions():
    assert can_generate_schedule("HR") is True
    assert can_generate_schedule("ADMIN") is True
