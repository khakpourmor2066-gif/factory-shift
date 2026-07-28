from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.access_requests.model import AccessRequest
from app.modules.access_requests.model import AccessRequest
from app.modules.access_requests.service import (
    activate_access_by_hr_identity,
    combine_pending_contact_with_code,
    format_contact_text,
    parse_identity_text,
)
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.users.model import User


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def test_parse_identity_text_extracts_mobile_and_personnel_code():
    assert parse_identity_text("ثبت 09120000002 EMP-001") == ("09120000002", "EMP-001")


def test_contact_text_is_combined_with_personnel_code():
    db = create_test_session()
    db.add(
        AccessRequest(
            platform="bale",
            messenger_user_id="999",
            latest_text=format_contact_text("+989120000002"),
            status="pending",
            request_count=1,
        )
    )
    db.commit()

    combined_text = combine_pending_contact_with_code(
        db,
        platform="bale",
        messenger_user_id="999",
        text="EMP-001",
    )

    assert combined_text == "ثبت 09120000002 EMP-001"
    db.close()


def test_hr_identity_activation_links_existing_employee_user():
    db = create_test_session()
    department = Department(name="Operations")
    user = User(mobile="09120000002", role="EMPLOYEE", messenger_user_id=None, is_active=True)
    db.add_all([department, user])
    db.commit()
    db.refresh(department)
    db.refresh(user)
    employee = Employee(
        personnel_code="EMP-001",
        first_name="Ali",
        last_name="Worker",
        mobile="09120000002",
        department_id=department.id,
        user_id=user.id,
    )
    db.add(employee)
    db.commit()

    approved, status, access_request_id = activate_access_by_hr_identity(
        db,
        platform="bale",
        messenger_user_id="999",
        text="ثبت 09120000002 EMP-001",
    )

    assert approved is True
    assert status == "approved"
    assert access_request_id is not None
    assert db.query(User).filter(User.id == user.id).first().messenger_user_id == "999"
    assert db.query(AccessRequest).filter(AccessRequest.id == access_request_id).first().status == "approved"
    db.close()


def test_hr_identity_activation_rejects_mismatch():
    db = create_test_session()
    department = Department(name="Operations")
    db.add(department)
    db.commit()
    db.refresh(department)
    db.add(
        Employee(
            personnel_code="EMP-001",
            first_name="Ali",
            last_name="Worker",
            mobile="09120000002",
            department_id=department.id,
        )
    )
    db.commit()

    approved, status, access_request_id = activate_access_by_hr_identity(
        db,
        platform="bale",
        messenger_user_id="999",
        text="ثبت 09129999999 EMP-001",
    )

    assert approved is False
    assert status == "identity_not_matched"
    assert access_request_id is None
    db.close()
