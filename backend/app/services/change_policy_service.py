"""Service-layer module for change policy service.
Implements business rules and orchestration for this domain area.
"""
class ChangePolicyService:
    """Service layer for change policy workflows."""
    def map_findings_to_interventions(self, findings: list[dict]) -> list[dict]:
        """Map findings to interventions."""
        interventions: list[dict] = []
        for finding in findings:
            f_type = finding["type"]
            if f_type == "HIGH_BOUNCE":
                interventions.append(
                    {
                        "variant_id": finding["variant_id"],
                        "change_type": "TRUST_SIGNAL",
                        "target_component": "hero.trust_callout",
                        "intent": "Strengthen trust and clarify guarantees",
                    }
                )
            elif f_type == "LOW_CTR":
                interventions.append(
                    {
                        "variant_id": finding["variant_id"],
                        "change_type": "CTA",
                        "target_component": "hero.cta_text",
                        "intent": "Increase click intent with clearer action",
                    }
                )
            elif f_type == "LOW_ATC_POST_CLICK":
                interventions.append(
                    {
                        "variant_id": finding["variant_id"],
                        "change_type": "COPY",
                        "target_component": "bullets",
                        "intent": "Emphasize purchase-driving benefits",
                    }
                )
        return interventions
