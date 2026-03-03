"""Pydantic schema module for lift trace.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from app.models.enums import ActorType, LiftEventType
from app.schemas.common import ORMModel


class LiftTraceEventResponse(ORMModel):
    """Pydantic schema for lift trace event response."""
    id: int
    campaign_id: int
    variant_id: int | None
    recommendation_id: int | None
    event_type: LiftEventType
    summary: str
    before_metrics_json: dict | None
    after_metrics_json: dict | None
    outcome_delta_json: dict | None
    actor_type: ActorType
    actor_id: int | None
    metadata_json: dict | None
    created_at: datetime
