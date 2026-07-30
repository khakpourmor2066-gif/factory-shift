from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.access_requests.model import AccessRequest
from app.modules.access_requests.service import (
    activate_access_by_hr_identity,
    build_access_request_review,
    combine_pending_contact_with_code,
    extract_contact_mobile,
    format_contact_text,
    normalize_mobile,
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


def test_typed_mobile_is_accepted_as_contact():
    assert extract_contact_mobile("09120000002") == "09120000002"
    assert extract_contact_mobile("۰۹۱۲۰۰۰۰۰۰۲") == "09120000002"
    assert normalize_mobile("+۹۸۹۱۲۰۰۰۰۰۰۲") == "09120000002"


def test_non_mobile_text_is_not_accepted_as_contact():
    assert extract_contact_mobile("EMP-001") is None
    assert extract_contact_mobile("شماره 09120000002") is None
    assert extract_contact_mobile("0912") is None


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


def test_typed_mobile_is_combined_with_personnel_code():
    db = create_test_session()
    db.add(
        AccessRequest(
            platform="bale",
            messenger_user_id="999",
            latest_text="09120000002",
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


def test_access_request_review_includes_matching_employee_details():
    db = create_test_session()
    department = Department(name="Operations")
    user = User(mobile="09120000002", role="SUPERVISOR", is_active=True)
    db.add_all([department, user])
    db.commit()
    db.refresh(department)
    db.refresh(user)
    db.add(
        Employee(
            personnel_code="SUP-001",
            first_name="Sara",
            last_name="Mohammadi",
            mobile="09120000002",
            department_id=department.id,
            user_id=user.id,
            is_active=True,
        )
    )
    access_request = AccessRequest(
        platform="bale",
        messenger_user_id="999",
        latest_text="ثبت 09120000002 SUP-001",
        status="pending",
        request_count=2,
    )
    db.add(access_request)
    db.commit()
    db.refresh(access_request)

    review = build_access_request_review(db, access_request)

    assert review["mobile"] == "09120000002"
    assert review["personnel_code"] == "SUP-001"
    assert review["employee_name"] == "Sara Mohammadi"
    assert review["employee_role"] == "SUPERVISOR"
    assert review["match_status"] == "matched"
    assert review["can_approve"] is True
    db.close()


def test_access_request_review_blocks_mismatched_employee_identity():
    db = create_test_session()
    department = Department(name="Operations")
    db.add(department)
    db.commit()
    db.refresh(department)
    db.add_all(
        [
            Employee(
                personnel_code="SUP-001",
                first_name="Sara",
                last_name="Mohammadi",
                mobile="09120000002",
                department_id=department.id,
                is_active=True,
            ),
            Employee(
                personnel_code="EMP-002",
                first_name="Reza",
                last_name="Karimi",
                mobile="09120000006",
                department_id=department.id,
                is_active=True,
            ),
        ]
    )
    access_request = AccessRequest(
        platform="bale",
        messenger_user_id="999",
        latest_text="ثبت 09120000002 EMP-002",
        status="pending",
        request_count=1,
    )
    db.add(access_request)
    db.commit()
    db.refresh(access_request)

    review = build_access_request_review(db, access_request)

    assert review["employee_name"] == "Reza Karimi"
    assert review["registered_mobile"] == "09120000006"
    assert review["registered_personnel_code"] == "SUP-001"
    assert review["match_status"] == "identity_mismatch"
    assert review["can_approve"] is False
    db.close()
