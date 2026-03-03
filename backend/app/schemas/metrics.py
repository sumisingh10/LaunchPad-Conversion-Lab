"""Pydantic schema module for metrics.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import MetricSource
from app.schemas.common import ORMModel


class MetricSnapshotResponse(ORMModel):
    """Pydantic schema for metric snapshot response."""
    id: int
    campaign_id: int
    variant_id: int
    timestamp: datetime
    impressions: int
    clicks: int
    add_to_cart: int
    bounces: int
    ctr: float
    atc_rate: float
    bounce_rate: float
    segment_json: dict | None
    source: MetricSource


class MetricsBatchResponse(BaseModel):
    """Pydantic schema for metrics batch response."""
    snapshots: list[MetricSnapshotResponse]
