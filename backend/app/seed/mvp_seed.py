from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User


def seed_mvp_data(db: Session) -> dict:
    department = _get_or_create_department(db)
    supervisor_user = _get_or_create_user(db, "09120000002", "SUPERVISOR", "sup-1")
    employee_user = _get_or_create_user(db, "09120000005", "EMPLOYEE", "emp-1")
    supervisor = _get_or_create_employee(
        db=db,
        personnel_code="SUP-001",
        first_name="Sara",
        last_name="Mohammadi",
        mobile="09120000002",
        department_id=department.id,
        supervisor_id=None,
        user_id=supervisor_user.id,
    )
    employee = _get_or_create_employee(
        db=db,
        personnel_code="EMP-001",
        first_name="Ali",
        last_name="Ahmadi",
        mobile="09120000005",
        department_id=department.id,
        supervisor_id=supervisor.id,
        user_id=employee_user.id,
    )
    pattern = _get_or_create_pattern(db)
    assignment = _get_or_create_assignment(db, employee.id, pattern.id)
    schedules = _get_or_create_schedules(db, employee.id, assignment.start_date)

    return {
        "department_id": department.id,
        "supervisor_user_id": supervisor_user.id,
        "employee_user_id": employee_user.id,
        "supervisor_employee_id": supervisor.id,
        "employee_id": employee.id,
        "pattern_id": pattern.id,
        "assignment_id": assignment.id,
        "schedule_count": len(schedules),
        "employee_messenger_user_id": employee_user.messenger_user_id,
        "supervisor_messenger_user_id": supervisor_user.messenger_user_id,
    }


def seed_active_employee_schedules(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> dict:
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")

    pattern = _get_or_create_pattern(db)
    employees = (
        db.query(Employee)
        .filter(Employee.is_active.is_(True))
        .order_by(Employee.id)
        .all()
    )
    assignments_created = 0
    schedules_created = 0
    total_days = (end_date - start_date).days + 1

    for employee in employees:
        assignment = (
            db.query(EmployeeShiftAssignment)
            .filter(EmployeeShiftAssignment.employee_id == employee.id)
            .filter(EmployeeShiftAssignment.pattern_id == pattern.id)
            .filter(EmployeeShiftAssignment.start_date == start_date)
            .first()
        )
        if assignment is None:
            assignment = EmployeeShiftAssignment(
                employee_id=employee.id,
                pattern_id=pattern.id,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(assignment)
            assignments_created += 1
        elif assignment.end_date is None or assignment.end_date < end_date:
            assignment.end_date = end_date

        existing_dates = {
            row[0]
            for row in (
                db.query(Schedule.date)
                .filter(Schedule.employee_id == employee.id)
                .filter(Schedule.date >= start_date)
                .filter(Schedule.date <= end_date)
                .all()
            )
        }
        for offset in range(total_days):
            schedule_date = start_date + timedelta(days=offset)
            if schedule_date in existing_dates:
                continue
            db.add(
                Schedule(
                    employee_id=employee.id,
                    date=schedule_date,
                    status="DAY" if (offset + employee.id) % 2 else "NIGHT",
                    generated_from="DEMO_ROSTER_SEED",
                    published=True,
                )
            )
            schedules_created += 1

    db.commit()
    return {
        "employee_count": len(employees),
        "assignments_created": assignments_created,
        "schedules_created": schedules_created,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def _get_or_create_department(db: Session) -> Department:
    department = db.query(Department).filter(Department.name == "Operations").first()
    if department is None:
        department = Department(name="Operations")
        db.add(department)
        db.commit()
        db.refresh(department)
    return department


def _get_or_create_user(db: Session, mobile: str, role: str, messenger_user_id: str) -> User:
    user = db.query(User).filter(User.mobile == mobile).first()
    if user is None:
        user = User(mobile=mobile, role=role, messenger_user_id=messenger_user_id)
        db.add(user)
    else:
        user.role = role
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def _get_or_create_employee(
    db: Session,
    personnel_code: str,
    first_name: str,
    last_name: str,
    mobile: str,
    department_id: int,
    supervisor_id: int | None,
    user_id: int,
) -> Employee:
    employee = db.query(Employee).filter(Employee.personnel_code == personnel_code).first()
    if employee is None:
        employee = Employee(
            personnel_code=personnel_code,
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            department_id=department_id,
            supervisor_id=supervisor_id,
            user_id=user_id,
        )
        db.add(employee)
    else:
        employee.first_name = first_name
        employee.last_name = last_name
        employee.mobile = mobile
        employee.department_id = department_id
        employee.supervisor_id = supervisor_id
        employee.user_id = user_id
        employee.is_active = True
    db.commit()
    db.refresh(employee)
    return employee


def _get_or_create_pattern(db: Session) -> ShiftPattern:
    pattern = db.query(ShiftPattern).filter(ShiftPattern.name == "MVP-2DAY").first()
    if pattern is None:
        pattern = ShiftPattern(name="MVP-2DAY", cycle_length=2, description="MVP two-day shift pattern")
        db.add(pattern)
        db.flush()
        db.add_all(
            [
                ShiftPatternDay(pattern_id=pattern.id, day_index=0, status="DAY"),
                ShiftPatternDay(pattern_id=pattern.id, day_index=1, status="NIGHT"),
            ]
        )
        db.commit()
        db.refresh(pattern)
    return pattern


def _get_or_create_assignment(db: Session, employee_id: int, pattern_id: int) -> EmployeeShiftAssignment:
    start_date = date(2026, 7, 1)
    assignment = (
        db.query(EmployeeShiftAssignment)
        .filter(EmployeeShiftAssignment.employee_id == employee_id)
        .filter(EmployeeShiftAssignment.pattern_id == pattern_id)
        .filter(EmployeeShiftAssignment.start_date == start_date)
        .first()
    )
    if assignment is None:
        assignment = EmployeeShiftAssignment(
            employee_id=employee_id,
            pattern_id=pattern_id,
            start_date=start_date,
            end_date=date(2026, 7, 31),
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
    return assignment


def _get_or_create_schedules(db: Session, employee_id: int, start_date: date) -> list[Schedule]:
    existing = (
        db.query(Schedule)
        .filter(Schedule.employee_id == employee_id)
        .filter(Schedule.date >= date(2026, 7, 1))
        .filter(Schedule.date <= date(2026, 7, 31))
        .order_by(Schedule.date)
        .all()
    )
    if len(existing) == 31:
        return existing

    existing_dates = {schedule.date for schedule in existing}
    schedules = list(existing)
    for offset in range(31):
        schedule_date = date(2026, 7, 1) + timedelta(days=offset)
        if schedule_date in existing_dates:
            continue
        schedules.append(
            Schedule(
                employee_id=employee_id,
                date=schedule_date,
                status="DAY" if (schedule_date - start_date).days % 2 == 0 else "NIGHT",
                generated_from="MVP_SEED",
                published=True,
            )
        )
    db.add_all([schedule for schedule in schedules if schedule.id is None])
    db.commit()
    return (
        db.query(Schedule)
        .filter(Schedule.employee_id == employee_id)
        .filter(Schedule.date >= date(2026, 7, 1))
        .filter(Schedule.date <= date(2026, 7, 31))
        .order_by(Schedule.date)
        .all()
    )
