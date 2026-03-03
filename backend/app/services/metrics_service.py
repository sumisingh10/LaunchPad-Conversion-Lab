"""Metrics service orchestration.

Coordinates KPI simulation, metric snapshot persistence, and Lift Trace logging
for campaign variants.
"""
from sqlalchemy.orm import Session

from app.models.enums import ActorType, LiftEventType
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.variant_repository import VariantRepository
from app.services.kpi_simulator_service import KPISimulatorService
from app.services.lift_trace_service import LiftTraceService


class MetricsService:
    """Business logic for metrics generation and retrieval."""

    def __init__(self, db: Session):
        """Initialize metrics, campaign, and variant dependencies for this session."""
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.variant_repo = VariantRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.simulator = KPISimulatorService()
        self.trace = LiftTraceService(db)

    def simulate_batch(self, campaign_id: int, user_id: int):
        """Simulate one KPI batch for every variant in a campaign and persist results."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user_id)
        if not campaign:
            raise ValueError("Campaign not found")

        variants = self.variant_repo.list_for_campaign(campaign_id)
        created = []
        for variant in variants:
            existing = self.metrics_repo.list_for_campaign(campaign_id, variant.id)
            batch_idx = len(existing) + 1
            snapshot = self.simulator.simulate_batch(campaign_id, variant, batch_idx, campaign.constraints_json)
            self.metrics_repo.create(snapshot)
            created.append(snapshot)
            self.trace.log(
                campaign_id=campaign_id,
                variant_id=variant.id,
                event_type=LiftEventType.METRICS_SIMULATED,
                summary=f"Simulated batch {batch_idx} for variant {variant.name}",
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                after_metrics_json={
                    "ctr": float(snapshot.ctr),
                    "atc_rate": float(snapshot.atc_rate),
                    "bounce_rate": float(snapshot.bounce_rate),
                },
            )
        self.db.commit()
        return created

    def list_metrics(self, campaign_id: int, variant_id: int | None = None):
        """Return metric snapshots for a campaign, optionally filtered to one variant."""
        return self.metrics_repo.list_for_campaign(campaign_id, variant_id)
