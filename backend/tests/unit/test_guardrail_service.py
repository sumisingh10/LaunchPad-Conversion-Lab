"""Unit tests for recommendation guardrail enforcement.
Verifies patch safety checks (drift, banned terms, required trust language) and scoring behavior.
"""
from app.schemas.patch import PatchDocument
from app.services.guardrail_service import GuardrailService


def sample_assets():
    """Provide fixture for sample assets."""
    return {
        "hero": {
            "headline": "Compact travel backpack",
            "subheadline": "Engineered for city commuters",
            "cta_text": "Shop Now",
            "trust_callout": "1-year warranty included",
        },
        "bullets": ["One one", "Two two", "Three three"],
        "banner": {"text": "Launch offer", "badge": "New"},
        "meta": {"strategy_tag": "value", "rationale": "seed"},
    }


def test_guardrail_blocks_large_change():
    """Verify guardrail blocks large change."""
    svc = GuardrailService()
    patch = PatchDocument.model_validate(
        {
            "operations": [
                {
                    "op": "replace",
                    "path": "hero.headline",
                    "value": "X" * 200,
                    "reason": "rewrite",
                }
            ]
        }
    )
    result = svc.assess_patch(sample_assets(), patch, {"max_char_delta_per_change": 30})
    assert result.allowed is False
    assert result.risk_level in {"MEDIUM", "HIGH"}


def test_guardrail_allows_small_change_and_scores():
    """Verify guardrail allows small change and scores."""
    svc = GuardrailService()
    patch = PatchDocument.model_validate(
        {
            "operations": [
                {
                    "op": "replace",
                    "path": "hero.cta_text",
                    "value": "Get Yours",
                    "reason": "clearer cta",
                }
            ]
        }
    )
    result = svc.assess_patch(sample_assets(), patch, {"max_char_delta_per_change": 30})
    assert result.allowed is True
    score = svc.recommendation_score(rank=1, risk_level=result.risk_level, has_metrics=True)
    assert score >= 80
