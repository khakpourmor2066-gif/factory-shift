from app.modules.access.permissions import can_view_own_schedule, can_view_supervisor_schedule


def test_employee_permissions():
    assert can_view_own_schedule("EMPLOYEE") is True
    assert can_view_supervisor_schedule("EMPLOYEE") is False


def test_supervisor_permissions():
    assert can_view_supervisor_schedule("SUPERVISOR") is True
