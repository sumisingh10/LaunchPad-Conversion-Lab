"""Repository module for metrics repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metric_snapshot import MetricSnapshot


class MetricsRepository:
    """Repository for metrics persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, metric: MetricSnapshot) -> MetricSnapshot:
        """Create and flush a new record."""
        self.db.add(metric)
        self.db.flush()
        return metric

    def list_for_campaign(self, campaign_id: int, variant_id: int | None = None) -> list[MetricSnapshot]:
        """Return records filtered by campaign id."""
        stmt = select(MetricSnapshot).where(MetricSnapshot.campaign_id == campaign_id)
        if variant_id is not None:
            stmt = stmt.where(MetricSnapshot.variant_id == variant_id)
        stmt = stmt.order_by(MetricSnapshot.timestamp.desc())
        return list(self.db.scalars(stmt).all())

    def latest_for_variant(self, campaign_id: int, variant_id: int) -> MetricSnapshot | None:
        """Fetch latest for variant."""
        stmt = (
            select(MetricSnapshot)
            .where(MetricSnapshot.campaign_id == campaign_id, MetricSnapshot.variant_id == variant_id)
            .order_by(MetricSnapshot.timestamp.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
