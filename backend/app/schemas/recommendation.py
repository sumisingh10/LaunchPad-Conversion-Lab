"""Pydantic schema module for recommendation.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ChangeType, RecommendationStatus
from app.schemas.common import ORMModel
from app.schemas.patch import PatchDocument


class ImprovementRecommendationResponse(ORMModel):
    """Pydantic schema for improvement recommendation response."""
    id: int
    campaign_id: int
    variant_id: int
    status: RecommendationStatus
    rank: int
    change_type: ChangeType
    target_component: str
    rationale: str
    hypothesis: str
    expected_impact_json: dict
    trigger_metrics_snapshot_id: int | None
    patch_json: dict
    codex_raw_response_json: dict | None
    created_at: datetime
    updated_at: datetime


class CodexImprovementRecommendation(BaseModel):
    """Pydantic schema for codex improvement recommendation."""
    rank: int
    change_type: ChangeType
    target_component: str
    rationale: str
    hypothesis: str
    expected_impact_json: dict
    patch: PatchDocument


class CodexRecommendationResponse(BaseModel):
    """Pydantic schema for codex recommendation response."""
    recommendations: list[CodexImprovementRecommendation]


class ProposeImprovementsRequest(BaseModel):
    """Pydantic schema for propose improvements request."""
    user_goal: str | None = None
    landing_page_snapshot_url: str | None = None
    focus_component: str | None = None
    selected_variant_id: int | None = None


class RecommendationApplyRequest(BaseModel):
    """Pydantic schema for recommendation apply request."""
    variant_name: str | None = None
