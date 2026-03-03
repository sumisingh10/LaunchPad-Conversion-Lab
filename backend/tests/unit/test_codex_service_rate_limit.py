"""Unit tests for Codex retry policy helpers.
Validates status-code retry decisions used by Codex API/CLI request orchestration.
"""
from app.schemas.recommendation import CodexRecommendationResponse
from app.services.codex_service import CodexService


def test_should_retry_for_rate_limit_and_server_errors():
    """Verify should retry for rate limit and server errors."""
    assert CodexService._should_retry(429) is True
    assert CodexService._should_retry(500) is True
    assert CodexService._should_retry(503) is True


def test_should_not_retry_for_client_errors():
    """Verify should not retry for client errors."""
    assert CodexService._should_retry(400) is False
    assert CodexService._should_retry(401) is False
    assert CodexService._should_retry(404) is False


def test_fallback_trust_focus_returns_three_with_required_phrase():
    """Ensure trust-focus fallback emits three trust-callout options honoring required phrase."""
    svc = CodexService()
    result = svc._fallback_recommendations(
        {
            "variant_id": 1,
            "focus_component": "hero.trust_callout",
            "campaign": {"constraints": {"required_trust_phrase": "free returns"}},
        }
    )
    assert len(result.recommendations) == 3
    for rec in result.recommendations:
        assert rec.target_component == "hero.trust_callout"
        assert rec.patch.operations[0].path == "hero.trust_callout"
        assert "free returns" in str(rec.patch.operations[0].value).lower()


def test_diversity_enforcement_backfills_three_trust_recommendations():
    """Ensure diversity layer backfills to three trust recs and preserves required trust phrase."""
    svc = CodexService()
    parsed = CodexRecommendationResponse.model_validate(
        {
            "recommendations": [
                {
                    "rank": 1,
                    "change_type": "TRUST_SIGNAL",
                    "target_component": "hero.trust_callout",
                    "rationale": "Trust improvements help reduce hesitation.",
                    "hypothesis": "Trust-copy clarity should reduce bounce.",
                    "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                    "patch": {
                        "operations": [
                            {
                                "op": "replace",
                                "path": "hero.trust_callout",
                                "value": "Secure checkout and quick delivery",
                                "reason": "Improve trust context",
                            }
                        ]
                    },
                }
            ]
        }
    )
    enforced = svc._ensure_recommendation_diversity(
        {
            "variant_id": 1,
            "focus_component": "hero.trust_callout",
            "selected_area_context": {"allowed_patch_paths": ["hero.trust_callout"]},
            "campaign": {"constraints": {"required_trust_phrase": "free returns"}},
        },
        parsed,
    )
    assert len(enforced.recommendations) == 3
    for rec in enforced.recommendations:
        op = rec.patch.operations[0]
        assert op.path == "hero.trust_callout"
        assert "free returns" in str(op.value).lower()
