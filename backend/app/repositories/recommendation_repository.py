"""Repository module for recommendation repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.improvement_recommendation import ImprovementRecommendation


class RecommendationRepository:
    """Repository for recommendation persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, recommendation: ImprovementRecommendation) -> ImprovementRecommendation:
        """Create and flush a new record."""
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def list_for_campaign(self, campaign_id: int) -> list[ImprovementRecommendation]:
        """Return records filtered by campaign id."""
        stmt = (
            select(ImprovementRecommendation)
            .where(ImprovementRecommendation.campaign_id == campaign_id)
            .order_by(ImprovementRecommendation.created_at.desc(), ImprovementRecommendation.rank.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get(self, recommendation_id: int) -> ImprovementRecommendation | None:
        """Return one record by primary identifier, if present."""
        return self.db.scalar(select(ImprovementRecommendation).where(ImprovementRecommendation.id == recommendation_id))
