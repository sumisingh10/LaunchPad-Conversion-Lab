"""Repository module for campaign repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign


class CampaignRepository:
    """Repository for campaign persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, campaign: Campaign) -> Campaign:
        """Create and flush a new record."""
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def list_for_user(self, user_id: int) -> list[Campaign]:
        """Return records filtered by user id."""
        stmt = select(Campaign).where(Campaign.user_id == user_id).order_by(Campaign.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, campaign_id: int, user_id: int) -> Campaign | None:
        """Return one record filtered by user id, if present."""
        stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user_id)
        return self.db.scalar(stmt)

    def delete_for_user(self, campaign_id: int, user_id: int) -> bool:
        """Delete one record filtered by user id and return success status."""
        campaign = self.get_for_user(campaign_id, user_id)
        if not campaign:
            return False
        self.db.delete(campaign)
        self.db.flush()
        return True
