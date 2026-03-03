"""Shared pytest configuration for backend tests.
Sets test environment variables, in-memory DB wiring, and reusable FastAPI test client fixtures.
"""
import os

os.environ["USE_SQLITE"] = "true"
os.environ["LOCAL_DATABASE_URL"] = "sqlite+pysqlite:///./test.db"
os.environ["CODEX_PROVIDER"] = "api"
os.environ["CODEX_USE_FALLBACK"] = "true"
os.environ["CODEX_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import get_db
from app.main import app
from app.models import Base

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Provide fixture for setup db."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """Provide fixture for db session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """Provide fixture for client."""
    def override_get_db():
        """Provide helper for override get db."""
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
