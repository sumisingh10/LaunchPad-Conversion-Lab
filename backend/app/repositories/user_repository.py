"""Repository module for user repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository for user persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, email: str, hashed_password: str, name: str | None) -> User:
        """Create and flush a new record."""
        user = User(email=email, hashed_password=hashed_password, name=name)
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_email(self, email: str) -> User | None:
        """Return one user by email address, if present."""
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: int) -> User | None:
        """Return one user by id, if present."""
        return self.db.scalar(select(User).where(User.id == user_id))
