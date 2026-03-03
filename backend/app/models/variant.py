"""ORM model definitions for variant.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import VariantSource


class Variant(Base):
    """ORM model for variant."""
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    assets_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[VariantSource] = mapped_column(Enum(VariantSource), nullable=False, default=VariantSource.HUMAN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    campaign = relationship("Campaign", back_populates="variants")
    versions = relationship("VariantVersion", back_populates="variant", cascade="all, delete-orphan")
    metric_snapshots = relationship("MetricSnapshot", back_populates="variant", cascade="all, delete-orphan")
    recommendations = relationship("ImprovementRecommendation", back_populates="variant", cascade="all, delete-orphan")
