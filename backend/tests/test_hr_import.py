from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.employees.hr_import_service import import_hr_employees_csv
from app.modules.employees.model import Employee
from app.modules.users.model import User


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def test_import_hr_employees_csv_creates_and_updates_rows(tmp_path: Path):
    db = create_test_session()
    csv_path = tmp_path / "hr.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-100,Ali,Worker,09120000100,EMPLOYEE\n"
        "SUP-100,Sara,Supervisor,09120000101,SUPERVISOR\n",
        encoding="utf-8",
    )

    first_result = import_hr_employees_csv(db, csv_path)
    second_result = import_hr_employees_csv(db, csv_path)

    assert first_result == {"created": 2, "updated": 0, "errors": []}
    assert second_result == {"created": 0, "updated": 2, "errors": []}
    assert db.query(Employee).count() == 2
    assert db.query(User).filter(User.role == "SUPERVISOR").count() == 1
    db.close()


def test_import_hr_employees_csv_reports_invalid_rows(tmp_path: Path):
    db = create_test_session()
    csv_path = tmp_path / "hr_invalid.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-100,Ali,Worker,123,EMPLOYEE\n"
        "EMP-101,Reza,Worker,09120000101,UNKNOWN\n",
        encoding="utf-8",
    )

    result = import_hr_employees_csv(db, csv_path)

    assert result["created"] == 0
    assert len(result["errors"]) == 2
    db.close()
