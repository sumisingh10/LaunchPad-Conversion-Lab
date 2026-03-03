"""Pydantic schema module for common.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Pydantic schema for o r m model."""
    model_config = ConfigDict(from_attributes=True)
