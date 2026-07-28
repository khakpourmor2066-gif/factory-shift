from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.modules.access_requests.model import AccessRequest
from app.modules.users.model import User
from tools.seed_access_demo import ensure_demo_access_requests
from tools.seed_scenarios import seed_scenario


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


def test_demo_access_requests_are_created():
    db = create_test_session()

    created = ensure_demo_access_requests(db)

    assert created == 5
    assert db.query(AccessRequest).count() == 5
    assert db.query(User).count() == 0
    db.close()


def test_demo_access_requests_are_idempotent():
    db = create_test_session()

    first_created = ensure_demo_access_requests(db)
    second_created = ensure_demo_access_requests(db)

    assert first_created == 5
    assert second_created == 0
    assert db.query(AccessRequest).count() == 5
    db.close()


def test_access_demo_scenario_seed_is_selectable():
    db = create_test_session()

    result = seed_scenario(db, "access_demo")

    assert result["scenario"] == "access_demo"
    assert result["access_requests_created"] == 5
    assert db.query(AccessRequest).count() == 5
    db.close()
