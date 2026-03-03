"""Pydantic schema module for codex.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel

from app.schemas.assets import CampaignAssets


class GeneratedVariant(BaseModel):
    """Pydantic schema for generated variant."""
    name: str
    strategy_tag: str
    rationale: str
    assets: CampaignAssets


class CodexVariantGenerationResponse(BaseModel):
    """Pydantic schema for codex variant generation response."""
    variants: list[GeneratedVariant]
