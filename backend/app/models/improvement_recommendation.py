"""ORM model definitions for improvement recommendation.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ChangeType, RecommendationStatus


class ImprovementRecommendation(Base):
    """ORM model for improvement recommendation."""
    __tablename__ = "improvement_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(Enum(RecommendationStatus), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType), nullable=False)
    target_component: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    trigger_metrics_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("metric_snapshots.id"), nullable=True)
    patch_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    codex_raw_response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    campaign = relationship("Campaign", back_populates="recommendations")
    variant = relationship("Variant", back_populates="recommendations")
