"""ORM model definitions for campaign.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CampaignObjective, CampaignStatus


class Campaign(Base):
    """ORM model for campaign."""
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[str] = mapped_column(String(255), nullable=False)
    product_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    objective: Mapped[CampaignObjective] = mapped_column(Enum(CampaignObjective), nullable=False)
    audience_segment: Mapped[str] = mapped_column(String(255), nullable=False)
    constraints_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    primary_kpi: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), nullable=False, default=CampaignStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="campaigns")
    variants = relationship("Variant", back_populates="campaign", cascade="all, delete-orphan")
    metric_snapshots = relationship("MetricSnapshot", back_populates="campaign", cascade="all, delete-orphan")
    recommendations = relationship("ImprovementRecommendation", back_populates="campaign", cascade="all, delete-orphan")
    lift_trace_events = relationship("LiftTraceEvent", back_populates="campaign", cascade="all, delete-orphan")
