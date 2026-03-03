"""API route module for lift trace endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.lift_trace import LiftTraceEventResponse
from app.services.lift_trace_service import LiftTraceService

router = APIRouter(tags=["lift-trace"])


@router.get("/campaigns/{campaign_id}/lift-trace", response_model=list[LiftTraceEventResponse])
def list_lift_trace(campaign_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return Lift Trace events for a campaign."""
    _ = current_user
    return LiftTraceService(db).list_events(campaign_id)
