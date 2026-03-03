"""ORM model definitions for variant version.
Declares persisted domain entities and relational mappings for LaunchPad Conversion Lab.
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CreatedBySystem


class VariantVersion(Base):
    """ORM model for variant version."""
    __tablename__ = "variant_versions"
    __table_args__ = (UniqueConstraint("variant_id", "version_number", name="uq_variant_version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    assets_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("variant_versions.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_system: Mapped[CreatedBySystem] = mapped_column(Enum(CreatedBySystem), nullable=False)
    change_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    variant = relationship("Variant", back_populates="versions")
