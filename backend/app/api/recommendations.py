"""API route module for recommendations endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse, FeedbackSummaryItem
from app.schemas.recommendation import ImprovementRecommendationResponse, RecommendationApplyRequest
from app.schemas.variant import VariantResponse
from app.services.feedback_service import FeedbackService
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["recommendations"])


@router.get("/campaigns/{campaign_id}/recommendations", response_model=list[ImprovementRecommendationResponse])
def list_recommendations(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return recommendations for a campaign."""
    _ = current_user
    return RecommendationService(db).list_recommendations(campaign_id)


@router.post("/recommendations/{recommendation_id}/approve", response_model=ImprovementRecommendationResponse)
def approve(recommendation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a recommendation as approved."""
    return RecommendationService(db).approve(recommendation_id, current_user)


@router.post("/recommendations/{recommendation_id}/reject", response_model=ImprovementRecommendationResponse)
def reject(recommendation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a recommendation as rejected."""
    return RecommendationService(db).reject(recommendation_id, current_user)


@router.post("/recommendations/{recommendation_id}/apply", response_model=ImprovementRecommendationResponse)
def apply(
    recommendation_id: int,
    payload: RecommendationApplyRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply recommendation patch to the target variant."""
    return RecommendationService(db).apply(recommendation_id, current_user, variant_name=(payload.variant_name if payload else None))


@router.post("/recommendations/{recommendation_id}/save-variant", response_model=VariantResponse)
def save_variant(
    recommendation_id: int,
    payload: RecommendationApplyRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save and return variant."""
    return RecommendationService(db).save_as_variant(recommendation_id, current_user, variant_name=(payload.variant_name if payload else None))


@router.post("/recommendations/{recommendation_id}/feedback", response_model=FeedbackResponse)
def create_feedback(
    recommendation_id: int,
    payload: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create and persist feedback."""
    return FeedbackService(db).create_feedback(recommendation_id, current_user, payload)


@router.get("/campaigns/{campaign_id}/feedback-summary", response_model=list[FeedbackSummaryItem])
def feedback_summary(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return aggregated recommendation feedback summary for a campaign."""
    _ = current_user
    return FeedbackService(db).feedback_summary(campaign_id)


@router.get("/campaigns/{campaign_id}/feedback", response_model=list[FeedbackResponse])
def list_feedback(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return recorded recommendation feedback for a campaign."""
    _ = current_user
    return FeedbackService(db).list_feedback(campaign_id)
