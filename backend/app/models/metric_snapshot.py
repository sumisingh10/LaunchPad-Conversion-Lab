"""ORM model definitions for metric snapshot.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MetricSource


class MetricSnapshot(Base):
    """ORM model for metric snapshot."""
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    add_to_cart: Mapped[int] = mapped_column(Integer, nullable=False)
    bounces: Mapped[int] = mapped_column(Integer, nullable=False)
    ctr: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    atc_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    bounce_rate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    segment_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[MetricSource] = mapped_column(Enum(MetricSource), nullable=False)

    campaign = relationship("Campaign", back_populates="metric_snapshots")
    variant = relationship("Variant", back_populates="metric_snapshots")
