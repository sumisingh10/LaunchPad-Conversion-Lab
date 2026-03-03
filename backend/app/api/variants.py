"""API route module for variants endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.variant import (
    ManualVariantEditRequest,
    VariantDeleteResponse,
    VariantResponse,
    VariantVersionPerformanceResponse,
)
from app.services.variant_service import VariantService

router = APIRouter(tags=["variants"])


@router.post("/campaigns/{campaign_id}/generate-variants", response_model=list[VariantResponse])
def generate_variants(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate campaign variants using Codex or fallback logic."""
    try:
        return VariantService(db).generate_variants(campaign_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/variants", response_model=list[VariantResponse])
def list_variants(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return variants for a campaign visible to the current user."""
    _ = current_user
    return VariantService(db).list_variants(campaign_id)


@router.delete("/variants/{variant_id}", response_model=VariantDeleteResponse)
def delete_variant(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a variant when it is not the campaign baseline."""
    try:
        return VariantService(db).delete_variant(variant_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/variants/{variant_id}/manual-edit", response_model=VariantResponse)
def manual_edit_variant(
    variant_id: int,
    payload: ManualVariantEditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute manual edit variant."""
    try:
        return VariantService(db).manual_edit_variant(variant_id, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/variants/{variant_id}/version-performance", response_model=list[VariantVersionPerformanceResponse])
def version_performance(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute version performance."""
    try:
        return VariantService(db).version_performance(variant_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/variants/{variant_id}/submit-admin-approval")
def submit_admin_approval(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a variant for simulated website admin approval."""
    try:
        return VariantService(db).submit_for_admin_approval(variant_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/variants/{variant_id}/admin-approval-status")
def admin_approval_status(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the simulated website-admin approval status for a variant."""
    try:
        return VariantService(db).admin_approval_status(variant_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
