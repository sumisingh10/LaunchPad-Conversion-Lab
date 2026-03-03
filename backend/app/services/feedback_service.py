"""Service-layer module for feedback service.
Implements business rules and orchestration for this domain area.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.recommendation_feedback import RecommendationFeedback
from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.feedback import FeedbackCreateRequest


class FeedbackService:
    """Service layer for feedback workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.repo = FeedbackRepository(db)
        self.reco_repo = RecommendationRepository(db)

    def create_feedback(self, recommendation_id: int, user: User, payload: FeedbackCreateRequest):
        """Create and persist feedback."""
        recommendation = self.reco_repo.get(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        feedback = RecommendationFeedback(
            recommendation_id=recommendation.id,
            campaign_id=recommendation.campaign_id,
            variant_id=recommendation.variant_id,
            user_id=user.id,
            sentiment=payload.sentiment,
            rating=payload.rating,
            comment=payload.comment,
        )
        self.repo.create(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def feedback_summary(self, campaign_id: int):
        """Return aggregated recommendation feedback summary for a campaign."""
        return self.repo.summary_for_campaign(campaign_id)

    def list_feedback(self, campaign_id: int):
        """Return recorded recommendation feedback for a campaign."""
        return self.repo.list_for_campaign(campaign_id)
