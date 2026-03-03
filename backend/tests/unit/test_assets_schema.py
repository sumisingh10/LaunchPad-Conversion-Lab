"""Unit tests for CampaignAssets schema validation.
Verifies strict asset contracts (hero fields, bullets count, banner/meta structure) used by generation and patching workflows.
"""
import pytest

from app.schemas.assets import CampaignAssets


def test_assets_schema_validates():
    """Verify assets schema validates."""
    payload = {
        "hero": {
            "headline": "Great deal now",
            "subheadline": "Best value for daily use",
            "cta_text": "Shop Now",
            "trust_callout": "1-year warranty",
        },
        "bullets": ["One", "Two", "Three"],
        "banner": {"text": "Limited offer", "badge": "New"},
        "meta": {"strategy_tag": "value", "rationale": "test"},
    }
    parsed = CampaignAssets.model_validate(payload)
    assert parsed.meta.strategy_tag == "value"


def test_assets_schema_rejects_invalid_bullets():
    """Verify assets schema rejects invalid bullets."""
    with pytest.raises(Exception):
        CampaignAssets.model_validate(
            {
                "hero": {"headline": "Hi there", "subheadline": "Sub", "cta_text": "Go", "trust_callout": "Trust"},
                "bullets": ["1", "2"],
                "banner": {"text": "Deal", "badge": None},
                "meta": {"strategy_tag": "x", "rationale": None},
            }
        )
