"""Campaign API routes.

Exposes authenticated CRUD and baseline-management endpoints used by the
Campaign Hub, Build Studio, and Compare Studio flows.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.campaign import CampaignBaselineRequest, CampaignCreateRequest, CampaignResponse
from app.services.campaign_service import CampaignService
from app.services.org_memory_service import OrgMemoryService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse)
def create_campaign(
    payload: CampaignCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new campaign owned by the current user."""
    return CampaignService(db).create_campaign(current_user, payload)


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all campaigns owned by the current user."""
    return CampaignService(db).list_campaigns(current_user)


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch one campaign by id for the current user."""
    return CampaignService(db).get_campaign(current_user, campaign_id)


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a campaign owned by the current user."""
    CampaignService(db).delete_campaign(current_user, campaign_id)
    return {"ok": True}


@router.post("/{campaign_id}/baseline", response_model=CampaignResponse)
def set_baseline(
    campaign_id: int,
    payload: CampaignBaselineRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a specific variant as the campaign baseline."""
    return CampaignService(db).set_baseline_variant(
        current_user,
        campaign_id,
        payload.variant_id,
        payload.baseline_name,
    )


@router.post("/{campaign_id}/baseline/revert", response_model=CampaignResponse)
def revert_baseline(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revert the campaign baseline selection to the original baseline."""
    return CampaignService(db).revert_baseline_variant(current_user, campaign_id)


@router.get("/{campaign_id}/org-insights")
def org_insights(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return synthetic cross-org benchmark insights for the campaign objective."""
    campaign = CampaignService(db).get_campaign(current_user, campaign_id)
    return OrgMemoryService().insights_for_objective(campaign.objective.value)
