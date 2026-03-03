"""Unit tests for KPI simulator determinism and bounds.
Ensures repeatable seeded outputs and valid metric ranges for campaign demo loops.
"""
from app.models.enums import VariantSource
from app.models.variant import Variant
from app.services.kpi_simulator_service import KPISimulatorService


def test_kpi_simulator_is_deterministic():
    """Verify kpi simulator is deterministic."""
    variant = Variant(
        id=1,
        campaign_id=1,
        name="A",
        strategy_tag="value",
        assets_json={
            "hero": {
                "headline": "Limited offer now",
                "subheadline": "Subheadline",
                "cta_text": "Shop Now",
                "trust_callout": "1-year warranty",
            },
            "bullets": ["One one", "Two two", "Three three"],
            "banner": {"text": "Deal", "badge": "New"},
            "meta": {"strategy_tag": "value", "rationale": "r"},
        },
        source=VariantSource.HUMAN,
    )
    svc = KPISimulatorService()
    one = svc.simulate_batch(1, variant, 1, {"required_trust_phrase": "warranty"})
    two = svc.simulate_batch(1, variant, 1, {"required_trust_phrase": "warranty"})
    assert one.impressions == two.impressions
    assert float(one.ctr) == float(two.ctr)
    assert 0 <= float(one.ctr) <= 1
