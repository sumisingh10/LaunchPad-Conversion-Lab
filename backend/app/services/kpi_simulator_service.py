"""Service-layer module for kpi simulator service.
Implements business rules and orchestration for this domain area.
"""
from datetime import datetime, timezone
import hashlib
import random

from app.models.enums import MetricSource
from app.models.metric_snapshot import MetricSnapshot
from app.models.variant import Variant


class KPISimulatorService:
    """Service layer for k p i simulator workflows."""
    CTA_VERBS = ("buy", "shop", "get", "claim", "start", "unlock")
    URGENCY_WORDS = ("now", "today", "limited", "hurry", "last chance")

    def _score_variant(self, variant: Variant, constraints: dict) -> tuple[float, float, float]:
        """Score a variant with deterministic KPI heuristics."""
        assets = variant.assets_json
        hero = assets.get("hero", {})
        headline = (hero.get("headline") or "").lower()
        cta = (hero.get("cta_text") or "").lower()
        trust = (hero.get("trust_callout") or "").lower()

        ctr = 0.05
        atc = 0.08
        bounce = 0.42

        if any(v in cta for v in self.CTA_VERBS):
            ctr += 0.01

        if trust.strip():
            atc += 0.01
            bounce -= 0.03

        if len(headline) > 80:
            ctr -= 0.012

        required_trust = str(constraints.get("required_trust_phrase", "")).lower().strip()
        if required_trust and required_trust not in trust:
            atc -= 0.01
            bounce += 0.04

        if any(word in headline for word in self.URGENCY_WORDS):
            ctr += 0.008
            bounce += 0.015

        return max(0.01, ctr), max(0.01, atc), min(0.9, max(0.05, bounce))

    def simulate_batch(self, campaign_id: int, variant: Variant, batch_index: int, constraints: dict) -> MetricSnapshot:
        """Simulate and return batch."""
        key = f"{campaign_id}:{variant.id}:{batch_index}"
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        base_ctr, base_atc, base_bounce = self._score_variant(variant, constraints)
        impressions = rng.randint(900, 1400)
        ctr = max(0.005, min(0.3, base_ctr + rng.uniform(-0.01, 0.01)))
        clicks = int(impressions * ctr)

        atc_rate = max(0.005, min(0.4, base_atc + rng.uniform(-0.015, 0.015)))
        add_to_cart = int(clicks * atc_rate)

        bounce_rate = max(0.05, min(0.95, base_bounce + rng.uniform(-0.03, 0.03)))
        bounces = int(clicks * bounce_rate)

        return MetricSnapshot(
            campaign_id=campaign_id,
            variant_id=variant.id,
            timestamp=datetime.now(timezone.utc),
            impressions=impressions,
            clicks=clicks,
            add_to_cart=add_to_cart,
            bounces=bounces,
            ctr=round(clicks / impressions if impressions else 0, 4),
            atc_rate=round(add_to_cart / clicks if clicks else 0, 4),
            bounce_rate=round(bounces / clicks if clicks else 0, 4),
            segment_json=None,
            source=MetricSource.SIMULATED,
        )
