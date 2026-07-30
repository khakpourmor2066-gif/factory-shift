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
    db.close()
