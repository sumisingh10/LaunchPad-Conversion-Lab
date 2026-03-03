"""ORM model definitions for lift trace event.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ActorType, LiftEventType


class LiftTraceEvent(Base):
    """ORM model for lift trace event."""
    __tablename__ = "lift_trace_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"), nullable=True)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("improvement_recommendations.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[LiftEventType] = mapped_column(Enum(LiftEventType), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    before_metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outcome_delta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    campaign = relationship("Campaign", back_populates="lift_trace_events")
