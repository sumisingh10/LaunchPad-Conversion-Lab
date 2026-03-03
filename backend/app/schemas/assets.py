"""Pydantic schema module for assets.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel, Field, field_validator


class HeroAssets(BaseModel):
    """Pydantic schema for hero assets."""
    headline: str = Field(min_length=3, max_length=140)
    subheadline: str = Field(min_length=3, max_length=220)
    cta_text: str = Field(min_length=2, max_length=80)
    trust_callout: str = Field(min_length=2, max_length=120)


class BannerAssets(BaseModel):
    """Pydantic schema for banner assets."""
    text: str = Field(min_length=2, max_length=120)
    badge: str | None = Field(default=None, max_length=50)


class MetaAssets(BaseModel):
    """Pydantic schema for meta assets."""
    strategy_tag: str = Field(min_length=2, max_length=50)
    rationale: str | None = Field(default=None, max_length=500)


class CampaignAssets(BaseModel):
    """Pydantic schema for campaign assets."""
    hero: HeroAssets
    bullets: list[str] = Field(min_length=3, max_length=3)
    banner: BannerAssets
    meta: MetaAssets

    @field_validator("bullets")
    @classmethod
    def validate_bullets(cls, value: list[str]) -> list[str]:
        """Ensure campaign assets include exactly three bullet items."""
        for bullet in value:
            if len(bullet.strip()) < 3:
                raise ValueError("Each bullet must be at least 3 chars")
        return value
