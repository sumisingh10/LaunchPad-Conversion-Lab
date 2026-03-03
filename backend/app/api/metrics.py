"""API route module for metrics endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.advisor import (
    AutoOptimizeJobStartResponse,
    AutoOptimizeJobStatusResponse,
    AutoOptimizeRequest,
    VariantAdviceJobStartResponse,
    VariantAdviceJobStatusResponse,
    VariantAdviceRequest,
    VariantAdviceResponse,
)
from app.schemas.metrics import MetricSnapshotResponse
from app.schemas.recommendation import ImprovementRecommendationResponse, ProposeImprovementsRequest
from app.services.advisor_service import AdvisorService
from app.services.advisor_job_service import AdvisorJobService
from app.services.auto_optimize_job_service import AutoOptimizeJobService
from app.services.metrics_service import MetricsService
from app.services.recommendation_service import RecommendationService

router = APIRouter(tags=["metrics"])


@router.post("/campaigns/{campaign_id}/simulate-batch", response_model=list[MetricSnapshotResponse])
def simulate_batch(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Simulate and return batch."""
    try:
        return MetricsService(db).simulate_batch(campaign_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/metrics", response_model=list[MetricSnapshotResponse])
def list_metrics(
    campaign_id: int,
    variant_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return metrics."""
    _ = current_user
    return MetricsService(db).list_metrics(campaign_id, variant_id)


@router.post("/campaigns/{campaign_id}/analyze-kpis")
def analyze_kpis(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Analyze and return kpis."""
    return RecommendationService(db).analyze_kpis(campaign_id, current_user)


@router.post("/campaigns/{campaign_id}/propose-improvements", response_model=list[ImprovementRecommendationResponse])
def propose(
    campaign_id: int,
    payload: ProposeImprovementsRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute propose."""
    return RecommendationService(db).propose_improvements(
        campaign_id,
        current_user,
        payload.user_goal if payload else None,
        payload.landing_page_snapshot_url if payload else None,
        payload.focus_component if payload else None,
        payload.selected_variant_id if payload else None,
    )


@router.post("/campaigns/{campaign_id}/advise-variants", response_model=VariantAdviceResponse)
def advise_variants(
    campaign_id: int,
    payload: VariantAdviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute advise variants."""
    try:
        return AdvisorService(db).advise(campaign_id, current_user, payload.user_goal, payload.variant_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/campaigns/{campaign_id}/advise-variants/jobs", response_model=VariantAdviceJobStartResponse)
def start_advise_variants_job(
    campaign_id: int,
    payload: VariantAdviceRequest,
    current_user: User = Depends(get_current_user),
):
    """Start a non-blocking best-variant advice job and return its poll id."""
    job = AdvisorJobService.start_job(
        campaign_id=campaign_id,
        user_id=current_user.id,
        user_goal=payload.user_goal,
        variant_ids=payload.variant_ids,
    )
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "created_at": job["created_at"],
    }


@router.get("/campaigns/{campaign_id}/advise-variants/jobs/{job_id}", response_model=VariantAdviceJobStatusResponse)
def get_advise_variants_job(
    campaign_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Return current status for an async best-variant advice job."""
    return AdvisorJobService.get_job(campaign_id=campaign_id, user_id=current_user.id, job_id=job_id)


@router.post("/campaigns/{campaign_id}/auto-optimize")
def auto_optimize(
    campaign_id: int,
    payload: AutoOptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply one automated optimization recommendation for compare flow."""
    return RecommendationService(db).auto_optimize(
        campaign_id,
        current_user,
        user_goal=payload.user_goal,
        preferred_variant_id=payload.preferred_variant_id,
    )


@router.post("/campaigns/{campaign_id}/auto-optimize/jobs", response_model=AutoOptimizeJobStartResponse)
def start_auto_optimize_job(
    campaign_id: int,
    payload: AutoOptimizeRequest,
    current_user: User = Depends(get_current_user),
):
    """Start a non-blocking auto-optimize job and return its poll id."""
    job = AutoOptimizeJobService.start_job(
        campaign_id=campaign_id,
        user_id=current_user.id,
        user_goal=payload.user_goal,
        preferred_variant_id=payload.preferred_variant_id,
    )
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "created_at": job["created_at"],
    }


@router.get("/campaigns/{campaign_id}/auto-optimize/jobs/{job_id}", response_model=AutoOptimizeJobStatusResponse)
def get_auto_optimize_job(
    campaign_id: int,
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Return current status for an async auto-optimize job."""
    return AutoOptimizeJobService.get_job(campaign_id=campaign_id, user_id=current_user.id, job_id=job_id)
