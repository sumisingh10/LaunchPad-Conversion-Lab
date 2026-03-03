"""Pydantic schema module for auth.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class SignUpRequest(BaseModel):
    """Pydantic schema for sign up request."""
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    """Pydantic schema for login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Pydantic schema for token response."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(ORMModel):
    """Pydantic schema for user response."""
    id: int
    email: EmailStr
    name: str | None
    created_at: datetime
