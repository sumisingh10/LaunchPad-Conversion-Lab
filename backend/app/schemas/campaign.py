"""Pydantic schema module for campaign.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import CampaignObjective, CampaignStatus
from app.schemas.common import ORMModel


class CampaignCreateRequest(BaseModel):
    """Pydantic schema for campaign create request."""
    name: str
    product_title: str
    product_category: str
    product_description: str
    objective: CampaignObjective
    audience_segment: str
    constraints_json: dict[str, Any] = {}
    primary_kpi: str
    status: CampaignStatus = CampaignStatus.DRAFT


class CampaignResponse(ORMModel):
    """Pydantic schema for campaign response."""
    id: int
    user_id: int
    name: str
    product_title: str
    product_category: str
    product_description: str
    objective: CampaignObjective
    audience_segment: str
    constraints_json: dict[str, Any]
    primary_kpi: str
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime


class CampaignBaselineRequest(BaseModel):
    """Pydantic schema for campaign baseline request."""
    variant_id: int
    baseline_name: str | None = None
