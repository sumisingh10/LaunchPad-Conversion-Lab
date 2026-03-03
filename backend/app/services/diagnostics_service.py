"""Service-layer module for diagnostics service.
Implements business rules and orchestration for this domain area.
"""
from collections import defaultdict

from app.models.metric_snapshot import MetricSnapshot


class DiagnosticsService:
    """Service layer for diagnostics workflows."""
    def analyze(self, snapshots: list[MetricSnapshot]) -> list[dict]:
        """Analyze KPI snapshots and emit diagnostic findings."""
        by_variant: dict[int, list[MetricSnapshot]] = defaultdict(list)
        for s in snapshots:
            by_variant[s.variant_id].append(s)

        if not by_variant:
            return []

        findings: list[dict] = []
        latest_by_variant: dict[int, MetricSnapshot] = {}
        for variant_id, variant_snaps in by_variant.items():
            latest = sorted(variant_snaps, key=lambda x: x.timestamp)[-1]
            latest_by_variant[variant_id] = latest
            if latest.bounce_rate > 0.55:
                findings.append({"variant_id": variant_id, "type": "HIGH_BOUNCE", "detail": "Bounce rate is elevated"})
            if latest.ctr < 0.04:
                findings.append({"variant_id": variant_id, "type": "LOW_CTR", "detail": "CTR is below target"})
            if latest.ctr > 0.06 and latest.atc_rate < 0.06:
                findings.append({"variant_id": variant_id, "type": "LOW_ATC_POST_CLICK", "detail": "ATC underperforms after click"})

        latest_rows = list(latest_by_variant.values())
        avg_ctr = sum(float(row.ctr) for row in latest_rows) / len(latest_rows)
        avg_atc = sum(float(row.atc_rate) for row in latest_rows) / len(latest_rows)
        winner = max(latest_rows, key=lambda row: float(row.ctr))
        findings.append(
            {
                "variant_id": winner.variant_id,
                "type": "TOP_PERFORMER",
                "detail": "Highest CTR in the latest batch. Use this copy as baseline.",
            }
        )

        for row in latest_rows:
            if float(row.ctr) < avg_ctr * 0.9:
                findings.append(
                    {
                        "variant_id": row.variant_id,
                        "type": "CTR_LAGGING",
                        "detail": "CTR is trailing campaign average. Prioritize headline and CTA clarity.",
                    }
                )
            if float(row.atc_rate) < avg_atc * 0.9:
                findings.append(
                    {
                        "variant_id": row.variant_id,
                        "type": "ATC_LAGGING",
                        "detail": "Add-to-cart rate trails average. Strengthen trust and product value cues.",
                    }
                )

        return findings
