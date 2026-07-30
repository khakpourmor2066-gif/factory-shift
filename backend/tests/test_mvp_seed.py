from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User
from app.seed.mvp_seed import seed_active_employee_schedules, seed_mvp_data


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def test_seed_mvp_data_is_repeatable():
    db = create_test_session()

    first_result = seed_mvp_data(db)
    second_result = seed_mvp_data(db)

    assert first_result["employee_messenger_user_id"] == "emp-1"
    assert first_result["supervisor_messenger_user_id"] == "sup-1"
    assert first_result["schedule_count"] == 31
    assert second_result["schedule_count"] == 31
    assert db.query(Department).count() == 1
    assert db.query(User).count() == 2
    assert db.query(Employee).count() == 2
    assert db.query(ShiftPattern).count() == 1
    assert db.query(ShiftPatternDay).count() == 2
    assert db.query(EmployeeShiftAssignment).count() == 1
    assert db.query(Schedule).count() == 31

    db.close()


def test_seed_mvp_data_matches_canonical_identity_and_preserves_real_messenger_link():
    db = create_test_session()
    supervisor_user = User(
        mobile="09120000002",
        role="EMPLOYEE",
        messenger_user_id="156546362",
        is_active=True,
    )
    db.add(supervisor_user)
    db.commit()

    seed_mvp_data(db)

    supervisor = db.query(Employee).filter(Employee.personnel_code == "SUP-001").one()
    employee = db.query(Employee).filter(Employee.personnel_code == "EMP-001").one()
    db.refresh(supervisor_user)

    assert supervisor.first_name == "Sara"
    assert supervisor.last_name == "Mohammadi"
    assert supervisor.mobile == "09120000002"
    assert supervisor.user_id == supervisor_user.id
    assert supervisor_user.role == "SUPERVISOR"
    assert supervisor_user.messenger_user_id == "156546362"
    assert employee.first_name == "Ali"
    assert employee.last_name == "Ahmadi"
    assert employee.mobile == "09120000005"

    db.close()


def test_seed_active_employee_schedules_covers_all_active_employees_repeatably():
    db = create_test_session()
    seed_mvp_data(db)
    department = db.query(Department).one()
    user = User(mobile="09120000006", role="EMPLOYEE", is_active=True)
    db.add(user)
    db.flush()
    db.add(
        Employee(
            personnel_code="EMP-002",
            first_name="Reza",
            last_name="Jafari",
            mobile="09120000006",
            department_id=department.id,
            user_id=user.id,
            is_active=True,
        )
    )
    db.commit()

    first_result = seed_active_employee_schedules(
        db,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    )
    second_result = seed_active_employee_schedules(
        db,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    )

    assert first_result["employee_count"] == 3
    assert first_result["assignments_created"] == 2
    assert first_result["schedules_created"] == 6
    assert second_result["assignments_created"] == 0
    assert second_result["schedules_created"] == 0
    assert db.query(EmployeeShiftAssignment).count() == 3
    assert db.query(Schedule).count() == 37
    db.close()
