from datetime import date
from types import SimpleNamespace

from app.modules.shifts.generator import generate_schedule_records


def test_generate_24_48_schedule_records():
    assignment = SimpleNamespace(employee_id=1, start_date=date(2026, 7, 1))
    pattern_days = [
        SimpleNamespace(day_index=0, status="WORK"),
        SimpleNamespace(day_index=1, status="REST"),
        SimpleNamespace(day_index=2, status="REST"),
    ]

    records = generate_schedule_records(
        assignment=assignment,
        pattern_days=pattern_days,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 4),
    )

    assert [record.status for record in records] == ["WORK", "REST", "REST", "WORK"]
