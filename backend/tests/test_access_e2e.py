from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.access_requests.model import AccessRequest
from app.modules.bot_adapter.handlers.bot_handler import resolve_user_message
from app.modules.bot_adapter.services.bale_webhook_service import resolve_bale_webhook_message
from app.modules.employees.hr_import_service import import_hr_employees_csv
from app.modules.users.model import User


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def test_hr_import_unknown_bale_activation_and_start_flow(tmp_path: Path, monkeypatch):
    db = create_test_session()
    csv_path = tmp_path / "hr.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-200,Ali,Worker,09120000200,EMPLOYEE\n",
        encoding="utf-8",
    )
    sent_messages = []

    monkeypatch.setattr(
        "app.modules.bot_adapter.services.bale_webhook_service.try_send_bale_message",
        lambda bot_adapter, user_id, text, reply_markup=None: sent_messages.append((user_id, text)) or True,
    )

    import_result = import_hr_employees_csv(db, csv_path)
    approval_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 999}, "text": "ثبت 09120000200 EMP-200"}},
    )
    user = db.query(User).filter(User.messenger_user_id == "999").first()
    start_result = resolve_user_message(db, user, "/start")

    assert import_result["created"] == 1
    assert approval_result["status"] == "access_approved"
    assert db.query(AccessRequest).first().status == "approved"
    assert user is not None
    assert start_result["type"] == "welcome"
    assert sent_messages[0][0] == "999"
    db.close()


def test_contact_then_personnel_code_activates_user(tmp_path: Path, monkeypatch):
    db = create_test_session()
    csv_path = tmp_path / "hr.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-201,Reza,Worker,09120000201,EMPLOYEE\n",
        encoding="utf-8",
    )
    sent_messages = []

    monkeypatch.setattr(
        "app.modules.bot_adapter.services.bale_webhook_service.try_send_bale_message",
        lambda bot_adapter, user_id, text, reply_markup=None: sent_messages.append((user_id, text, reply_markup)) or True,
    )

    import_hr_employees_csv(db, csv_path)
    contact_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1001}, "contact": {"phone_number": "+989120000201"}}},
    )
    approval_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1001}, "text": "EMP-201"}},
    )
    user = db.query(User).filter(User.messenger_user_id == "1001").first()

    assert contact_result["status"] == "contact_received"
    assert approval_result["status"] == "access_approved"
    assert user is not None
    assert sent_messages[0][2] is None
    assert sent_messages[0][1] == (
        "شماره تلفن همراه دریافت شد.\n"
        "شماره: 09120000201\n"
        "اکنون، شماره کارمندی خود را ارسال کنید. مثال:\n"
        "EMP-001\n"
        "\n"
        "تعداد درخواست در حال بررسی: 1"
    )
    db.close()


def test_typed_mobile_then_personnel_code_activates_user(tmp_path: Path, monkeypatch):
    db = create_test_session()
    csv_path = tmp_path / "hr.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-202,Mina,Worker,09120000202,EMPLOYEE\n",
        encoding="utf-8",
    )
    sent_messages = []

    monkeypatch.setattr(
        "app.modules.bot_adapter.services.bale_webhook_service.try_send_bale_message",
        lambda bot_adapter, user_id, text, reply_markup=None: sent_messages.append((user_id, text, reply_markup)) or True,
    )

    import_hr_employees_csv(db, csv_path)
    contact_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1002}, "text": "09120000202"}},
    )
    approval_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1002}, "text": "EMP-202"}},
    )
    user = db.query(User).filter(User.messenger_user_id == "1002").first()

    assert contact_result["status"] == "contact_received"
    assert contact_result["contact_mobile"] == "09120000202"
    assert approval_result["status"] == "access_approved"
    assert user is not None
    assert "شماره تلفن همراه دریافت شد." in sent_messages[0][1]
    assert "شناسه بله شما" not in sent_messages[0][1]
    assert "شماره درخواست دسترسی" not in sent_messages[0][1]
    assert "تعداد درخواست در حال بررسی: 1" in sent_messages[0][1]
    db.close()


def test_user_can_logout_and_activate_again(tmp_path: Path, monkeypatch):
    db = create_test_session()
    csv_path = tmp_path / "hr.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-203,Navid,Worker,09120000203,EMPLOYEE\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.modules.bot_adapter.services.bale_webhook_service.try_send_bale_message",
        lambda *args, **kwargs: True,
    )

    import_hr_employees_csv(db, csv_path)
    first_activation = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1003}, "text": "ثبت 09120000203 EMP-203"}},
    )
    user = db.query(User).filter(User.messenger_user_id == "1003").first()
    logout_result = resolve_user_message(db, user, "LOGOUT_CONFIRM")
    contact_result = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1003}, "text": "09120000203"}},
    )
    second_activation = resolve_bale_webhook_message(
        db,
        {"message": {"chat": {"id": 1003}, "text": "EMP-203"}},
    )
    approved_requests = (
        db.query(AccessRequest)
        .filter(AccessRequest.messenger_user_id == "1003")
        .filter(AccessRequest.status == "approved")
        .count()
    )

    assert first_activation["status"] == "access_approved"
    assert logout_result["type"] == "logged_out"
    assert contact_result["status"] == "contact_received"
    assert second_activation["status"] == "access_approved"
    assert approved_requests == 2
    assert db.query(User).filter(User.messenger_user_id == "1003").first() is not None
    db.close()
