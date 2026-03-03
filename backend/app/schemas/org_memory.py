"""Pydantic schema module for org memory.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel


class OrgInsight(BaseModel):
    """Pydantic schema for org insight."""
    change_type: str
    segment: str
    avg_ctr_lift: float
    avg_atc_lift: float
    avg_bounce_delta: float
    avg_sentiment_delta: float
