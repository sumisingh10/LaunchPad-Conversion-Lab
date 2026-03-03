"""Unit tests for KPI diagnostics heuristics.
Checks that snapshot patterns are correctly flagged into actionable findings for the recommendation pipeline.
"""
from datetime import datetime, timezone

from app.models.enums import MetricSource
from app.models.metric_snapshot import MetricSnapshot
from app.services.diagnostics_service import DiagnosticsService


def test_diagnostics_flags_expected_patterns():
    """Verify diagnostics flags expected patterns."""
    snapshots = [
        MetricSnapshot(
            campaign_id=1,
            variant_id=10,
            timestamp=datetime.now(timezone.utc),
            impressions=1000,
            clicks=30,
            add_to_cart=1,
            bounces=20,
            ctr=0.03,
            atc_rate=0.03,
            bounce_rate=0.66,
            source=MetricSource.SIMULATED,
        )
    ]
    findings = DiagnosticsService().analyze(snapshots)
    kinds = {f["type"] for f in findings}
    assert "LOW_CTR" in kinds
    assert "HIGH_BOUNCE" in kinds
