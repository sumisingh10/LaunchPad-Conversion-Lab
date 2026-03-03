"""Repository module for lift trace repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.lift_trace_event import LiftTraceEvent


class LiftTraceRepository:
    """Repository for lift trace persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, event: LiftTraceEvent) -> LiftTraceEvent:
        """Create and flush a new record."""
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_campaign(self, campaign_id: int) -> list[LiftTraceEvent]:
        """Return records filtered by campaign id."""
        stmt = select(LiftTraceEvent).where(LiftTraceEvent.campaign_id == campaign_id).order_by(LiftTraceEvent.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_for_variant(self, campaign_id: int, variant_id: int, limit: int = 25) -> list[LiftTraceEvent]:
        """Return recent lift-trace events scoped to a campaign variant."""
        stmt = (
            select(LiftTraceEvent)
            .where(LiftTraceEvent.campaign_id == campaign_id, LiftTraceEvent.variant_id == variant_id)
            .order_by(desc(LiftTraceEvent.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
