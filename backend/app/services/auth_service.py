"""Service-layer module for auth service.
Implements business rules and orchestration for this domain area.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, SignUpRequest


class AuthService:
    """Service layer for auth workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.user_repo = UserRepository(db)

    def signup(self, payload: SignUpRequest) -> str:
        """Register a new user and return a token."""
        if self.user_repo.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        user = self.user_repo.create(payload.email, hash_password(payload.password), payload.name)
        self.db.commit()
        return create_access_token(str(user.id))

    def login(self, payload: LoginRequest) -> str:
        """Authenticate user credentials and return a token."""
        user = self.user_repo.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return create_access_token(str(user.id))
