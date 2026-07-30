from datetime import date
from types import SimpleNamespace

import pytest

from app.modules.shifts import router, service
from app.modules.shifts.schema import (
    EmployeeShiftAssignmentCreate,
    ScheduleGenerateRequest,
    ShiftPatternCreate,
)


def build_request(employee_id: int = 1) -> ScheduleGenerateRequest:
    return ScheduleGenerateRequest(
        employee_id=employee_id,
        assignment_id=10,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 3),
        publish=True,
    )


def test_generate_schedule_only_fills_missing_dates(monkeypatch):
    assignment = SimpleNamespace(
        employee_id=1,
        pattern_id=20,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    pattern_days = [
        SimpleNamespace(day_index=0, status="WORK"),
        SimpleNamespace(day_index=1, status="REST"),
    ]
    saved_records = []

    monkeypatch.setattr(service, "get_assignment", lambda db, assignment_id: assignment)
    monkeypatch.setattr(service, "get_pattern_days", lambda db, pattern_id: pattern_days)
    monkeypatch.setattr(
        service,
        "list_employee_schedule",
        lambda db, employee_id, from_date, to_date: [SimpleNamespace(date=date(2026, 7, 2))],
    )
    monkeypatch.setattr(
        service,
        "save_schedules",
        lambda db, records: saved_records.extend(records) or records,
    )

    result = service.generate_schedule(None, build_request())

    assert [record.date for record in result] == [date(2026, 7, 1), date(2026, 7, 3)]
    assert [record.date for record in saved_records] == [date(2026, 7, 1), date(2026, 7, 3)]


def test_generate_schedule_rejects_assignment_for_another_employee(monkeypatch):
    assignment = SimpleNamespace(
        employee_id=2,
        pattern_id=20,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    monkeypatch.setattr(service, "get_assignment", lambda db, assignment_id: assignment)

    with pytest.raises(ValueError, match="assignment does not belong to employee"):
        service.generate_schedule(None, build_request(employee_id=1))


def test_generate_schedule_rejects_dates_outside_assignment(monkeypatch):
    assignment = SimpleNamespace(
        employee_id=1,
        pattern_id=20,
        start_date=date(2026, 7, 2),
        end_date=date(2026, 7, 2),
    )
    monkeypatch.setattr(service, "get_assignment", lambda db, assignment_id: assignment)

    with pytest.raises(ValueError, match="before assignment"):
        service.generate_schedule(None, build_request())


def test_shift_management_endpoints_are_limited_to_hr_and_admin(monkeypatch):
    allowed_role_sets = []
    current_user = SimpleNamespace(role="HR")
    monkeypatch.setattr(
        router,
        "require_roles",
        lambda user, roles: allowed_role_sets.append(roles),
    )
    monkeypatch.setattr(router, "register_shift_pattern", lambda db, payload: payload)
    monkeypatch.setattr(router, "register_assignment", lambda db, payload: payload)
    monkeypatch.setattr(router, "generate_schedule", lambda db, payload: [])

    router.create_pattern_endpoint(
        ShiftPatternCreate(name="24/48", days=["WORK", "REST", "REST"]),
        None,
        current_user,
    )
    router.create_assignment_endpoint(
        EmployeeShiftAssignmentCreate(
            employee_id=1,
            pattern_id=1,
            start_date=date(2026, 7, 1),
        ),
        None,
        current_user,
    )
    router.generate_schedule_endpoint(build_request(), None, current_user)

    assert allowed_role_sets == [{"HR", "ADMIN"}, {"HR", "ADMIN"}, {"HR", "ADMIN"}]
