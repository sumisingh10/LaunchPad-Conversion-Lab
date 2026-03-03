"""Service-layer module for org memory service.
Implements business rules and orchestration for this domain area.
"""
class OrgMemoryService:
    """Synthetic cross-org memory for demo comparison and recommendation context."""

    def insights_for_objective(self, objective: str) -> list[dict]:
        """Return synthetic cross-organization insights for the objective."""
        base = [
            {
                "change_type": "TRUST_SIGNAL",
                "segment": "first_time_shoppers",
                "avg_ctr_lift": 0.9,
                "avg_atc_lift": 1.6,
                "avg_bounce_delta": -1.2,
                "avg_sentiment_delta": 0.8,
            },
            {
                "change_type": "CTA",
                "segment": "mobile_first",
                "avg_ctr_lift": 1.4,
                "avg_atc_lift": 0.4,
                "avg_bounce_delta": 0.2,
                "avg_sentiment_delta": 0.3,
            },
            {
                "change_type": "COPY",
                "segment": "premium_intent",
                "avg_ctr_lift": 0.7,
                "avg_atc_lift": 1.1,
                "avg_bounce_delta": -0.4,
                "avg_sentiment_delta": 0.6,
            },
        ]
        if objective == "ATC":
            return sorted(base, key=lambda x: x["avg_atc_lift"], reverse=True)
        if objective == "CTR":
            return sorted(base, key=lambda x: x["avg_ctr_lift"], reverse=True)
        return base
