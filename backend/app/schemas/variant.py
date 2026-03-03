"""Pydantic schema module for variant.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import VariantSource
from app.schemas.assets import CampaignAssets
from app.schemas.common import ORMModel


class VariantCreate(BaseModel):
    """Pydantic schema for variant create."""
    name: str
    strategy_tag: str
    assets: CampaignAssets
    source: VariantSource


class VariantResponse(ORMModel):
    """Pydantic schema for variant response."""
    id: int
    campaign_id: int
    name: str
    strategy_tag: str
    assets_json: dict
    source: VariantSource
    created_at: datetime
    updated_at: datetime


class VariantVersionResponse(ORMModel):
    """Pydantic schema for variant version response."""
    id: int
    variant_id: int
    version_number: int
    assets_json: dict
    change_summary: str
    created_at: datetime


class ManualVariantEditRequest(BaseModel):
    """Pydantic schema for manual variant edit request."""
    path: str
    value: str | None
    reason: str | None = None
    variant_name: str | None = None


class VariantVersionPerformanceResponse(BaseModel):
    """Pydantic schema for variant version performance response."""
    version_id: int
    version_number: int
    created_at: datetime
    avg_ctr: float | None
    avg_atc_rate: float | None
    avg_bounce_rate: float | None
    estimated_spend: float
    sentiment_score: float | None


class VariantDeleteResponse(BaseModel):
    """Pydantic schema for variant deletion response payload."""
    ok: bool
    variant_id: int
    variant_name: str
    message: str
