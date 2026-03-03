"""Repository module for feedback repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.improvement_recommendation import ImprovementRecommendation
from app.models.recommendation_feedback import RecommendationFeedback


class FeedbackRepository:
    """Repository for feedback persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, feedback: RecommendationFeedback) -> RecommendationFeedback:
        """Create and flush a new record."""
        self.db.add(feedback)
        self.db.flush()
        return feedback

    def list_for_campaign(self, campaign_id: int) -> list[RecommendationFeedback]:
        """Return records filtered by campaign id."""
        stmt = (
            select(RecommendationFeedback)
            .where(RecommendationFeedback.campaign_id == campaign_id)
            .order_by(RecommendationFeedback.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def summary_for_campaign(self, campaign_id: int) -> list[dict]:
        """Aggregate feedback metrics grouped for a campaign."""
        stmt = (
            select(
                RecommendationFeedback.recommendation_id,
                func.sum(case((RecommendationFeedback.sentiment == "POSITIVE", 1), else_=0)).label("positive_count"),
                func.sum(case((RecommendationFeedback.sentiment == "NEGATIVE", 1), else_=0)).label("negative_count"),
                func.avg(RecommendationFeedback.rating).label("avg_rating"),
            )
            .where(RecommendationFeedback.campaign_id == campaign_id)
            .group_by(RecommendationFeedback.recommendation_id)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "recommendation_id": int(r.recommendation_id),
                "positive_count": int(r.positive_count or 0),
                "negative_count": int(r.negative_count or 0),
                "avg_rating": float(r.avg_rating) if r.avg_rating is not None else None,
            }
            for r in rows
        ]

    def summary_by_change_type_for_campaign(self, campaign_id: int) -> list[dict]:
        """Summarize by change type for campaign."""
        stmt = (
            select(
                ImprovementRecommendation.change_type,
                func.sum(case((RecommendationFeedback.sentiment == "POSITIVE", 1), else_=0)).label("positive_count"),
                func.sum(case((RecommendationFeedback.sentiment == "NEGATIVE", 1), else_=0)).label("negative_count"),
                func.avg(RecommendationFeedback.rating).label("avg_rating"),
            )
            .join(
                ImprovementRecommendation,
                ImprovementRecommendation.id == RecommendationFeedback.recommendation_id,
            )
            .where(RecommendationFeedback.campaign_id == campaign_id)
            .group_by(ImprovementRecommendation.change_type)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "change_type": str(r.change_type),
                "positive_count": int(r.positive_count or 0),
                "negative_count": int(r.negative_count or 0),
                "avg_rating": float(r.avg_rating) if r.avg_rating is not None else None,
            }
            for r in rows
        ]

    def sentiment_for_variant(self, campaign_id: int, variant_id: int) -> dict:
        """Return average sentiment and sample count for a variant."""
        stmt = (
            select(
                func.sum(case((RecommendationFeedback.sentiment == "POSITIVE", 1), else_=0)).label("positive_count"),
                func.sum(case((RecommendationFeedback.sentiment == "NEGATIVE", 1), else_=0)).label("negative_count"),
                func.avg(RecommendationFeedback.rating).label("avg_rating"),
            )
            .where(
                RecommendationFeedback.campaign_id == campaign_id,
                RecommendationFeedback.variant_id == variant_id,
            )
        )
        row = self.db.execute(stmt).one()
        return {
            "positive_count": int(row.positive_count or 0),
            "negative_count": int(row.negative_count or 0),
            "avg_rating": float(row.avg_rating) if row.avg_rating is not None else None,
        }
