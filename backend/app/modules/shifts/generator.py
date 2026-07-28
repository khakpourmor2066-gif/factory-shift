from datetime import date, timedelta

from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPatternDay


def generate_schedule_records(
    assignment: EmployeeShiftAssignment,
    pattern_days: list[ShiftPatternDay],
    from_date: date,
    to_date: date,
    publish: bool = False,
) -> list[Schedule]:
    if from_date > to_date:
        raise ValueError("from_date must be before or equal to to_date")

    days_by_index = {pattern_day.day_index: pattern_day for pattern_day in pattern_days}
    cycle_length = len(days_by_index)
    if cycle_length == 0:
        raise ValueError("shift pattern must have at least one day")

    records: list[Schedule] = []
    current_date = from_date
    while current_date <= to_date:
        offset = (current_date - assignment.start_date).days
        day_index = offset % cycle_length
        pattern_day = days_by_index[day_index]
        records.append(
            Schedule(
                employee_id=assignment.employee_id,
                date=current_date,
                status=pattern_day.status,
                generated_from="GENERATOR",
                published=publish,
            )
        )
        current_date += timedelta(days=1)

    return records
