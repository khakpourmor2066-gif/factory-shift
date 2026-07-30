from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import Schedule
from app.modules.supervisor_view.service import get_supervisor_schedule
from app.modules.users.model import User


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def add_employee(db, department, *, code, mobile, role, supervisor_id=None):
    user = User(mobile=mobile, role=role, is_active=True)
    db.add(user)
    db.flush()
    employee = Employee(
        personnel_code=code,
        first_name=code,
        last_name="Test",
        mobile=mobile,
        department_id=department.id,
        supervisor_id=supervisor_id,
        user_id=user.id,
        is_active=True,
    )
    db.add(employee)
    db.flush()
    return user, employee


def test_hr_sees_all_published_employees_for_day():
    db = create_test_session()
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    hr_user, hr_employee = add_employee(
        db,
        department,
        code="HR-001",
        mobile="09120000001",
        role="HR",
    )
    _, first_employee = add_employee(
        db,
        department,
        code="EMP-001",
        mobile="09120000002",
        role="EMPLOYEE",
    )
    _, second_employee = add_employee(
        db,
        department,
        code="EMP-002",
        mobile="09120000003",
        role="EMPLOYEE",
    )
    target_date = date(2026, 7, 30)
    db.add_all(
        [
            Schedule(employee_id=hr_employee.id, date=target_date, status="DAY", published=True),
            Schedule(employee_id=first_employee.id, date=target_date, status="NIGHT", published=True),
            Schedule(employee_id=second_employee.id, date=target_date, status="DAY", published=True),
        ]
    )
    db.commit()

    result = get_supervisor_schedule(db, hr_user, target_date)

    assert len(result["employees"]) == 3
    assert {item["employee_id"] for item in result["employees"]} == {
        hr_employee.id,
        first_employee.id,
        second_employee.id,
    }
    db.close()


def test_supervisor_sees_only_direct_reports():
    db = create_test_session()
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    supervisor_user, supervisor = add_employee(
        db,
        department,
        code="SUP-001",
        mobile="09120000001",
        role="SUPERVISOR",
    )
    _, direct_report = add_employee(
        db,
        department,
        code="EMP-001",
        mobile="09120000002",
        role="EMPLOYEE",
        supervisor_id=supervisor.id,
    )
    _, other_employee = add_employee(
        db,
        department,
        code="EMP-002",
        mobile="09120000003",
        role="EMPLOYEE",
    )
    target_date = date(2026, 7, 30)
    db.add_all(
        [
            Schedule(employee_id=direct_report.id, date=target_date, status="DAY", published=True),
            Schedule(employee_id=other_employee.id, date=target_date, status="NIGHT", published=True),
        ]
    )
    db.commit()

    result = get_supervisor_schedule(db, supervisor_user, target_date)

    assert [item["employee_id"] for item in result["employees"]] == [direct_report.id]
    db.close()
