"""Unit tests for structured patch application.
Verifies allowed replace operations update assets correctly and invalid paths are rejected.
"""
import pytest

from app.schemas.patch import PatchDocument
from app.services.patch_apply_service import PatchApplyService


def test_patch_apply_service_updates_assets():
    """Verify patch apply service updates assets."""
    assets = {
        "hero": {"headline": "Old", "subheadline": "Sub", "cta_text": "Shop", "trust_callout": "Trust"},
        "bullets": ["One one", "Two two", "Three three"],
        "banner": {"text": "Banner", "badge": "B"},
        "meta": {"strategy_tag": "value", "rationale": "r"},
    }
    patch = PatchDocument.model_validate(
        {"operations": [{"op": "replace", "path": "hero.headline", "value": "New Headline", "reason": "Improve CTR"}]}
    )
    updated = PatchApplyService().apply_patch(assets, patch)
    assert updated["hero"]["headline"] == "New Headline"


def test_patch_apply_rejects_bad_structure():
    """Verify patch apply rejects bad structure."""
    assets = {
        "hero": {"headline": "Old", "subheadline": "Sub", "cta_text": "Shop", "trust_callout": "Trust"},
        "bullets": ["One one", "Two two", "Three three"],
        "banner": {"text": "Banner", "badge": "B"},
        "meta": {"strategy_tag": "value", "rationale": "r"},
    }
    patch = PatchDocument.model_validate(
        {"operations": [{"op": "replace", "path": "bullets.1", "value": "x", "reason": "bad"}]}
    )
    with pytest.raises(ValueError):
        PatchApplyService().apply_patch(assets, patch)
