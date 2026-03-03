"""Unit tests for change policy mapping logic.
Ensures diagnostics findings are translated into expected intervention targets for recommendation planning.
"""
from app.services.change_policy_service import ChangePolicyService


def test_change_policy_maps_findings():
    """Verify change policy maps findings."""
    findings = [{"variant_id": 3, "type": "LOW_CTR", "detail": "x"}]
    interventions = ChangePolicyService().map_findings_to_interventions(findings)
    assert interventions[0]["target_component"] == "hero.cta_text"
