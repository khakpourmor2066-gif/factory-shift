from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main
from app.database.connection import Base, get_db
from app.main import app
from app.modules.access.dependencies import get_current_user
from app.modules.bot_adapter.handlers.bot_handler import resolve_user_message
from app.modules.change_management.model import AuditLog
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.schedule_generation.model import ScheduleGenerationJob
from app.modules.schedule_generation.schema import ScheduleGenerationPreviewCreate
from app.modules.schedule_generation.service import (
    cancel_generation_job,
    confirm_generation_job,
    create_generation_preview,
    publish_generation_job,
)
from app.modules.shifts.model import EmployeeShiftAssignment, Schedule, ShiftPattern, ShiftPatternDay
from app.modules.users.model import User


def create_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    department = Department(name="Operations")
    hr_user = User(mobile="09120000101", role="HR", is_active=True)
    employee_user = User(mobile="09120000102", role="EMPLOYEE", is_active=True)
    db.add_all([department, hr_user, employee_user])
    db.flush()
    employee = Employee(
        personnel_code="EMP-GEN",
        first_name="Ali",
        last_name="Ahmadi",
        mobile=employee_user.mobile,
        department_id=department.id,
        user_id=employee_user.id,
        is_active=True,
    )
    pattern = ShiftPattern(name="24/48-GEN", cycle_length=3)
    db.add_all([employee, pattern])
    db.flush()
    db.add_all(
        [
            ShiftPatternDay(pattern_id=pattern.id, day_index=0, status="WORK"),
            ShiftPatternDay(pattern_id=pattern.id, day_index=1, status="REST"),
            ShiftPatternDay(pattern_id=pattern.id, day_index=2, status="REST"),
        ]
    )
    assignment = EmployeeShiftAssignment(
        employee_id=employee.id,
        pattern_id=pattern.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=40),
    )
    db.add(assignment)
    db.commit()
    db.refresh(hr_user)
    db.refresh(employee)
    db.refresh(assignment)
    return db, hr_user, employee_user, employee, assignment


def preview_payload(employee, assignment, days: int = 3):
    return ScheduleGenerationPreviewCreate(
        employee_id=employee.id,
        assignment_id=assignment.id,
        from_date=date.today(),
        to_date=date.today() + timedelta(days=days - 1),
    )


def test_preview_confirm_and_publish_lifecycle():
    db, hr_user, _, employee, assignment = create_context()
    db.add(
        Schedule(
            employee_id=employee.id,
            date=date.today() + timedelta(days=1),
            status="REST",
            generated_from="IMPORT",
            published=True,
        )
    )
    db.commit()

    job = create_generation_preview(db, preview_payload(employee, assignment), hr_user.id)

    assert job.status == "PENDING"
    assert job.total_days == 3
    assert job.missing_days == 2
    assert db.query(Schedule).count() == 1

    confirmed = confirm_generation_job(db, job.id, hr_user.id)

    assert confirmed.status == "CONFIRMED"
    assert confirmed.created_schedules == 2
    generated = db.query(Schedule).filter(Schedule.generated_from == f"GEN_JOB:{job.id}").all()
    assert len(generated) == 2
    assert all(schedule.published is False for schedule in generated)

    published = publish_generation_job(db, job.id, hr_user.id)

    assert published.status == "PUBLISHED"
    assert all(schedule.published is True for schedule in generated)
    assert db.query(AuditLog).filter(AuditLog.action == "schedule_generation_published").count() == 1
    db.close()


def test_cancel_does_not_create_schedules():
    db, hr_user, _, employee, assignment = create_context()
    job = create_generation_preview(db, preview_payload(employee, assignment), hr_user.id)

    cancelled = cancel_generation_job(db, job.id, hr_user.id)

    assert cancelled.status == "CANCELLED"
    assert db.query(Schedule).count() == 0
    db.close()


def test_schedule_generation_api_enforces_roles_and_returns_options():
    db, hr_user, employee_user, employee, assignment = create_context()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: hr_user
    client = TestClient(app)
    try:
        options = client.get("/schedule-generation/options")
        assert options.status_code == 200
        assert options.json()["employees"][0]["personnel_code"] == "EMP-GEN"

        preview = client.post(
            "/schedule-generation/preview",
            json={
                "employee_id": employee.id,
                "assignment_id": assignment.id,
                "from_date": date.today().isoformat(),
                "to_date": (date.today() + timedelta(days=2)).isoformat(),
            },
        )
        assert preview.status_code == 200
        assert preview.json()["status"] == "PENDING"

        app.dependency_overrides[get_current_user] = lambda: employee_user
        denied = client.get("/schedule-generation/options")
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_schedule_generator_web_page_contains_full_workflow():
    client = TestClient(app)

    response = client.get("/admin/schedule-generator")

    assert response.status_code == 200
    assert "انتخاب کارمند" in response.text
    assert "الگوی اختصاص‌یافته" in response.text
    assert "مشاهده پیش‌نمایش" in response.text
    assert "تأیید و ذخیره پیش‌نویس" in response.text
    assert "انتشار برنامه" in response.text
    assert "لغو" in response.text


def test_bale_generation_flow_creates_preview_and_can_cancel():
    db, hr_user, _, employee, assignment = create_context()

    employee_step = resolve_user_message(db, hr_user, "تولید برنامه")
    assignment_step = resolve_user_message(db, hr_user, f"GEN_EMP:{employee.id}")
    range_step = resolve_user_message(db, hr_user, f"GEN_ASSIGN:{assignment.id}")
    preview_step = resolve_user_message(db, hr_user, f"GEN_RANGE:{assignment.id}:7D")
    job_id = preview_step["data"]["job"]["id"]
    cancel_step = resolve_user_message(db, hr_user, f"GEN_CANCEL:{job_id}")

    assert employee_step["type"] == "schedule_generation_employee_select"
    assert assignment_step["type"] == "schedule_generation_assignment_select"
    assert range_step["type"] == "schedule_generation_range_select"
    assert preview_step["type"] == "schedule_generation_preview"
    assert preview_step["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == f"GEN_CONFIRM:{job_id}"
    assert cancel_step["type"] == "schedule_generation_result"
    assert db.query(ScheduleGenerationJob).filter_by(id=job_id).one().status == "CANCELLED"
    assert db.query(Schedule).count() == 0
    db.close()
