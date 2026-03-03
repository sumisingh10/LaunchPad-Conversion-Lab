"""Pydantic schema module for patch.
Defines typed request/response and validation contracts for API and service boundaries.
"""
from pydantic import BaseModel, Field, field_validator

ALLOWED_PATHS = {
    "hero.headline",
    "hero.subheadline",
    "hero.cta_text",
    "hero.trust_callout",
    "bullets.0",
    "bullets.1",
    "bullets.2",
    "banner.text",
    "banner.badge",
    "meta.strategy_tag",
    "meta.rationale",
}


class PatchOperation(BaseModel):
    """Pydantic schema for patch operation."""
    op: str = Field(default="replace")
    path: str
    value: str | None
    reason: str = Field(min_length=3, max_length=300)

    @field_validator("op")
    @classmethod
    def only_replace(cls, value: str) -> str:
        """Execute only replace."""
        if value != "replace":
            raise ValueError("Only replace op is supported")
        return value

    @field_validator("path")
    @classmethod
    def valid_path(cls, value: str) -> str:
        """Execute valid path."""
        if value not in ALLOWED_PATHS:
            raise ValueError(f"Unsupported patch path: {value}")
        return value


class PatchDocument(BaseModel):
    """Pydantic schema for patch document."""
    operations: list[PatchOperation] = Field(min_length=1, max_length=10)
