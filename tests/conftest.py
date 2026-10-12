"""Pytest test configuration and fixtures.

Sets up an in-memory SQLite database using StaticPool and a temporary certificate
storage directory for isolated, fast, and deterministic test runs.
"""

from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import app.database as app_db
import app.services.job_processor as job_proc
from app.core.config import settings
from app.database import Base, get_db
from app.main import app

# In-memory SQLite with StaticPool ensures all threads/sessions share the same DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Override application settings with temporary test storage paths."""
    temp_dir = tmp_path_factory.mktemp("test_certificates")
    settings.CERTIFICATE_OUTPUT_DIR = str(temp_dir)

    # Patch SessionLocal across database and background job modules
    app_db.SessionLocal = TestingSessionLocal
    job_proc.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_database():
    """Create database schema before each test and drop after test completion."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a direct database session for test assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture with database dependency override."""
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
