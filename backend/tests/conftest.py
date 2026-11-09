"""
Shared fixtures. Every test gets a fresh in-memory SQLite DB (no Postgres
needed) and a fresh recovery vault in a temp directory.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.domains.auth.models import User  # noqa: F401  (registers the table)
from app.domains.recovery.models import RecoveryAction  # noqa: F401
from app.domains.auth.service import _login_limiter
from app.domains.recovery.service import RecoveryService
from app.main import app


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    original_factory = RecoveryService.session_factory
    RecoveryService.session_factory = factory
    RecoveryService.reset_vault(tmp_path / "vault")
    RecoveryService._suspended.clear()
    RecoveryService._active_incident_id = None
    _login_limiter._failures.clear()  # each test starts with no failed logins
    yield factory
    RecoveryService.session_factory = original_factory


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
