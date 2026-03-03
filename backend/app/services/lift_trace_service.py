"""Service-layer module for lift trace service.
Implements business rules and orchestration for this domain area.
"""
from sqlalchemy.orm import Session

from app.models.enums import ActorType, LiftEventType
from app.models.lift_trace_event import LiftTraceEvent
from app.repositories.lift_trace_repository import LiftTraceRepository


class LiftTraceService:
    """Service layer for lift trace workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.repo = LiftTraceRepository(db)

    def log(
        self,
        campaign_id: int,
        variant_id: int | None,
        event_type: LiftEventType,
        summary: str,
        actor_type: ActorType,
        actor_id: int | None = None,
        recommendation_id: int | None = None,
        before_metrics_json: dict | None = None,
        after_metrics_json: dict | None = None,
        outcome_delta_json: dict | None = None,
        metadata_json: dict | None = None,
    ) -> LiftTraceEvent:
        """Execute log."""
        event = LiftTraceEvent(
            campaign_id=campaign_id,
            variant_id=variant_id,
            recommendation_id=recommendation_id,
            event_type=event_type,
            summary=summary,
            actor_type=actor_type,
            actor_id=actor_id,
            before_metrics_json=before_metrics_json,
            after_metrics_json=after_metrics_json,
            outcome_delta_json=outcome_delta_json,
            metadata_json=metadata_json,
        )
        self.repo.create(event)
        return event

    def list_events(self, campaign_id: int):
        """Return Lift Trace events for a campaign."""
        return self.repo.list_for_campaign(campaign_id)
