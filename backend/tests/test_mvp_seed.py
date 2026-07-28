from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User
from app.seed.mvp_seed import seed_mvp_data


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
