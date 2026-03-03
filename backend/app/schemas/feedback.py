"""Pydantic schema module for feedback.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FeedbackSentiment


class FeedbackCreateRequest(BaseModel):
    """Pydantic schema for feedback create request."""
    sentiment: FeedbackSentiment
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    """Pydantic schema for feedback response."""
    id: int
    recommendation_id: int
    campaign_id: int
    variant_id: int
    user_id: int | None
    sentiment: FeedbackSentiment
    rating: int | None
    comment: str | None
    created_at: datetime


class FeedbackSummaryItem(BaseModel):
    """Pydantic schema for feedback summary item."""
    recommendation_id: int
    positive_count: int
    negative_count: int
    avg_rating: float | None
