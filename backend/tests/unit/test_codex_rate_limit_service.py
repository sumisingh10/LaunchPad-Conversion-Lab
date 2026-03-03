"""Unit tests for Codex request rate limiting.
Confirms per-user/per-operation threshold enforcement and expected HTTP 429 behavior on limit exceedance.
"""
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.codex_rate_limit_service import CodexRateLimitService


def test_rate_limit_triggers_after_threshold(monkeypatch):
    """Verify rate limit triggers after threshold."""
    svc = CodexRateLimitService()

    monkeypatch.setattr(settings, "codex_requests_per_minute", 2)

    # isolate key for this test user/operation
    for _ in range(2):
        svc.check(999, "propose_improvements")

    with pytest.raises(HTTPException) as exc:
        svc.check(999, "propose_improvements")

    assert exc.value.status_code == 429
