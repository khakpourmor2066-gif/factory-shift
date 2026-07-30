from io import BytesIO
from datetime import date

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.main import app
from app.modules.access.dependencies import get_current_user
from app.modules.data_imports.model import ImportError, ImportJob
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import Schedule
from app.modules.users.model import User


def create_test_context(role: str = "ADMIN"):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    user = User(mobile="09120000999", role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), db, user


def close_test_context(db):
    app.dependency_overrides.clear()
    db.close()


def test_employee_csv_preview_and_confirm():
    client, db, _ = create_test_context("HR")
    content = (
        "employee_code,first_name,last_name,mobile,department,role,supervisor_code\n"
        "SUP-001,سارا,محمدی,09120000001,عملیات,SUPERVISOR,\n"
        "EMP-001,علی,احمدی,09120000002,عملیات,EMPLOYEE,SUP-001\n"
    )
    try:
        preview = client.post(
            "/imports/employees/preview",
            files={"file": ("employees.csv", content.encode("utf-8"), "text/csv")},
        )
        assert preview.status_code == 200
        payload = preview.json()
        assert payload["job"]["status"] == "PENDING"
        assert payload["job"]["valid_rows"] == 2
        assert payload["errors"] == []

        confirmed = client.post(f"/imports/{payload['job']['id']}/confirm")
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "COMPLETED"
        assert confirmed.json()["imported_rows"] == 2

        employee = db.query(Employee).filter(Employee.personnel_code == "EMP-001").one()
        supervisor = db.query(Employee).filter(Employee.personnel_code == "SUP-001").one()
        assert employee.supervisor_id == supervisor.id
        assert db.query(Department).filter(Department.name == "عملیات").count() == 1

        rolled_back = client.post(f"/imports/{payload['job']['id']}/rollback")
        assert rolled_back.status_code == 200
        assert rolled_back.json()["status"] == "ROLLED_BACK"
        assert db.query(Employee).count() == 0
    finally:
        close_test_context(db)


def test_employee_preview_persists_row_errors_and_can_be_rejected():
    client, db, _ = create_test_context("HR")
    content = (
        "employee_code,first_name,last_name,mobile,department,role\n"
        "EMP-001,علی,احمدی,123,عملیات,EMPLOYEE\n"
    )
    try:
        preview = client.post(
            "/imports/employees/preview",
            files={"file": ("employees.csv", content.encode("utf-8"), "text/csv")},
        )
        assert preview.status_code == 200
        payload = preview.json()
        assert payload["job"]["valid_rows"] == 0
        assert payload["job"]["rejected_rows"] == 1
        assert payload["errors"][0]["error_code"] == "invalid_mobile"
        assert db.query(ImportError).count() == 1

        rejected = client.post(f"/imports/{payload['job']['id']}/reject")
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "REJECTED"
        assert db.query(Employee).count() == 0
    finally:
        close_test_context(db)


def test_employee_preview_rejects_unknown_supervisor_and_mobile_conflict():
    client, db, _ = create_test_context("HR")
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    db.add(
        Employee(
            personnel_code="EMP-EXISTING",
            first_name="Existing",
            last_name="Employee",
            mobile="09120000300",
            department_id=department.id,
            is_active=True,
        )
    )
    db.commit()
    content = (
        "employee_code,first_name,last_name,mobile,department,role,supervisor_code\n"
        "EMP-NEW,New,Employee,09120000300,Operations,EMPLOYEE,SUP-MISSING\n"
    )
    try:
        response = client.post(
            "/imports/employees/preview",
            files={"file": ("employees.csv", content.encode("utf-8"), "text/csv")},
        )
        assert response.status_code == 200
        error_codes = {error["error_code"] for error in response.json()["errors"]}
        assert error_codes == {"mobile_conflict", "supervisor_not_found"}
        assert response.json()["job"]["rejected_rows"] == 1
    finally:
        close_test_context(db)


def test_shift_csv_preview_and_confirm_upserts_schedule():
    client, db, _ = create_test_context("SUPERVISOR")
    department = Department(name="عملیات")
    db.add(department)
    db.flush()
    employee = Employee(
        personnel_code="EMP-001",
        first_name="علی",
        last_name="احمدی",
        mobile="09120000001",
        department_id=department.id,
        is_active=True,
    )
    db.add(employee)
    db.commit()
    content = (
        "employee_code,shift_date,shift_name,shift_code,start_time,end_time\n"
        "EMP-001,2026-07-30,روز,DAY,08:00,16:00\n"
    )
    try:
        preview = client.post(
            "/imports/shifts/preview",
            files={"file": ("shifts.csv", content.encode("utf-8"), "text/csv")},
        )
        assert preview.status_code == 200
        job_id = preview.json()["job"]["id"]
        assert client.post(f"/imports/{job_id}/confirm").status_code == 200
        schedule = db.query(Schedule).one()
        assert schedule.status == "DAY"
        assert schedule.shift_name == "روز"
        assert schedule.start_time.isoformat(timespec="minutes") == "08:00"
        assert schedule.end_time.isoformat(timespec="minutes") == "16:00"
        assert schedule.generated_from == "IMPORT"
        assert schedule.published is True
    finally:
        close_test_context(db)


def test_shift_preview_rejects_reversed_time_range():
    client, db, _ = create_test_context("SUPERVISOR")
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    db.add(
        Employee(
            personnel_code="EMP-001",
            first_name="Ali",
            last_name="Ahmadi",
            mobile="09120000001",
            department_id=department.id,
            is_active=True,
        )
    )
    db.commit()
    content = (
        "employee_code,shift_date,shift_name,shift_code,start_time,end_time\n"
        "EMP-001,2026-07-30,روز,DAY,16:00,08:00\n"
    )
    try:
        response = client.post(
            "/imports/shifts/preview",
            files={"file": ("shifts.csv", content.encode("utf-8"), "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["errors"][0]["error_code"] == "invalid_time_range"
    finally:
        close_test_context(db)


def test_xlsx_employee_preview_is_supported():
    client, db, _ = create_test_context("HR")
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["employee_code", "first_name", "last_name", "mobile", "department", "role"])
    worksheet.append(["EMP-001", "Ali", "Ahmadi", "09120000001", "Operations", "EMPLOYEE"])
    content = BytesIO()
    workbook.save(content)
    try:
        response = client.post(
            "/imports/employees/preview",
            files={
                "file": (
                    "employees.xlsx",
                    content.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 200
        assert response.json()["job"]["valid_rows"] == 1
    finally:
        close_test_context(db)


def test_import_routes_enforce_roles_and_templates_are_reachable():
    client, db, _ = create_test_context("EMPLOYEE")
    try:
        forbidden = client.post(
            "/imports/employees/preview",
            files={"file": ("employees.csv", b"employee_code\nEMP-1\n", "text/csv")},
        )
        assert forbidden.status_code == 403
    finally:
        close_test_context(db)

    client, db, _ = create_test_context("ADMIN")
    try:
        employee_template = client.get("/imports/templates/employees")
        shift_template = client.get("/imports/templates/shifts")
        assert employee_template.status_code == 200
        assert employee_template.json()["filename"] == "employees_template.csv"
        assert shift_template.status_code == 200
        assert shift_template.json()["filename"] == "shifts_template.csv"
        assert db.query(ImportJob).count() == 0
    finally:
        close_test_context(db)


def test_hr_can_preview_and_confirm_shift_import():
    client, db, user = create_test_context("HR")
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    db.add(
        Employee(
            personnel_code="EMP-HR-001",
            first_name="Ali",
            last_name="Ahmadi",
            mobile="09120000401",
            department_id=department.id,
            is_active=True,
        )
    )
    db.commit()
    content = (
        "employee_code,shift_date,shift_name,shift_code,start_time,end_time\n"
        "EMP-HR-001,2026-08-02,روز,DAY,08:00,16:00\n"
    )
    try:
        template_response = client.get("/imports/templates/shifts")
        assert template_response.status_code == 200

        preview = client.post(
            "/imports/shifts/preview",
            files={"file": ("shifts.csv", content.encode("utf-8"), "text/csv")},
        )
        assert preview.status_code == 200
        job_id = preview.json()["job"]["id"]
        response = client.post(f"/imports/{job_id}/confirm")
        assert response.status_code == 200
        assert db.query(Schedule).filter(Schedule.date == date(2026, 8, 2)).count() == 1
    finally:
        close_test_context(db)


def test_employee_template_is_self_contained_for_preview():
    client, db, _ = create_test_context("HR")
    try:
        template_response = client.get("/imports/templates/employees")
        assert template_response.status_code == 200
        template = template_response.json()
        preview = client.post(
            "/imports/employees/preview",
            files={
                "file": (
                    template["filename"],
                    template["content"].encode("utf-8"),
                    template["content_type"],
                )
            },
        )
        assert preview.status_code == 200
        assert preview.json()["job"]["valid_rows"] == 2
        assert preview.json()["errors"] == []
    finally:
        close_test_context(db)


def test_shift_import_rollback_restores_existing_schedule():
    client, db, _ = create_test_context("SUPERVISOR")
    department = Department(name="Operations")
    db.add(department)
    db.flush()
    employee = Employee(
        personnel_code="EMP-200",
        first_name="Reza",
        last_name="Karimi",
        mobile="09120000200",
        department_id=department.id,
        is_active=True,
    )
    db.add(employee)
    db.flush()
    original = Schedule(
        employee_id=employee.id,
        date=date(2026, 8, 1),
        status="OFF",
        generated_from="GENERATOR",
        published=False,
    )
    db.add(original)
    db.commit()
    content = (
        "employee_code,shift_date,shift_name,shift_code,start_time,end_time\n"
        "EMP-200,2026-08-01,روز,DAY,08:00,16:00\n"
    )
    try:
        preview = client.post(
            "/imports/shifts/preview",
            files={"file": ("shifts.csv", content.encode("utf-8"), "text/csv")},
        )
        job_id = preview.json()["job"]["id"]
        assert client.post(f"/imports/{job_id}/confirm").status_code == 200
        db.refresh(original)
        assert original.status == "DAY"

        rollback = client.post(f"/imports/{job_id}/rollback")
        assert rollback.status_code == 200
        db.refresh(original)
        assert original.status == "OFF"
        assert original.generated_from == "GENERATOR"
        assert original.published is False
    finally:
        close_test_context(db)
