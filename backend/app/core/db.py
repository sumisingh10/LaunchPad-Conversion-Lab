"""Core runtime module for db.
Provides shared runtime primitives such as config, auth, DB, and logging.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def get_database_url() -> str:
    """Resolve the configured database URL for the current runtime mode."""
    return settings.local_database_url if settings.use_sqlite else settings.database_url


database_url = get_database_url()
engine = create_engine(
    database_url,
    future=True,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """Yield a database session for request-scoped dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
