"""Pydantic schema module for advisor.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel, Field


class VariantAdviceRequest(BaseModel):
    """Pydantic schema for variant advice request."""
    user_goal: str = Field(min_length=3, max_length=500)
    variant_ids: list[int] | None = None


class VariantAdviceResponse(BaseModel):
    """Pydantic schema for variant advice response."""
    best_variant_id: int
    best_variant_name: str | None = None
    confidence: float = Field(ge=0, le=1)
    rationale: str
    next_step: str


class VariantAdviceJobStartResponse(BaseModel):
    """Pydantic schema for starting an asynchronous best-variant advice job."""
    job_id: str
    status: str
    created_at: str


class VariantAdviceJobStatusResponse(BaseModel):
    """Pydantic schema for current asynchronous best-variant advice job status."""
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class AutoOptimizeRequest(BaseModel):
    """Pydantic schema for auto optimize request."""
    user_goal: str = Field(min_length=3, max_length=500)
    preferred_variant_id: int | None = None


class AutoOptimizeJobStartResponse(BaseModel):
    """Pydantic schema for starting an asynchronous auto-optimize job."""
    job_id: str
    status: str
    created_at: str


class AutoOptimizeJobStatusResponse(BaseModel):
    """Pydantic schema for current asynchronous auto-optimize job status."""
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None
    created_at: str
    updated_at: str
