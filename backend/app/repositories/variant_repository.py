"""Repository module for variant repository.
Encapsulates database read/write patterns used by service-layer workflows.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.variant import Variant
from app.models.variant_version import VariantVersion


class VariantRepository:
    """Repository for variant persistence operations."""
    def __init__(self, db: Session):
        """Initialize repository with an active database session."""
        self.db = db

    def create(self, variant: Variant) -> Variant:
        """Create and flush a new record."""
        self.db.add(variant)
        self.db.flush()
        return variant

    def list_for_campaign(self, campaign_id: int) -> list[Variant]:
        """Return records filtered by campaign id."""
        stmt = select(Variant).where(Variant.campaign_id == campaign_id).order_by(Variant.created_at.asc())
        return list(self.db.scalars(stmt).all())

    def get(self, variant_id: int) -> Variant | None:
        """Return one record by primary identifier, if present."""
        return self.db.scalar(select(Variant).where(Variant.id == variant_id))

    def delete(self, variant: Variant) -> None:
        """Delete a variant row from persistence."""
        self.db.delete(variant)

    def create_version(self, version: VariantVersion) -> VariantVersion:
        """Create and persist version."""
        self.db.add(version)
        self.db.flush()
        return version

    def next_version_number(self, variant_id: int) -> int:
        """Compute next version number."""
        max_ver = self.db.scalar(select(func.max(VariantVersion.version_number)).where(VariantVersion.variant_id == variant_id))
        return (max_ver or 0) + 1

    def latest_version(self, variant_id: int) -> VariantVersion | None:
        """Return the latest saved version for a variant."""
        stmt = (
            select(VariantVersion)
            .where(VariantVersion.variant_id == variant_id)
            .order_by(VariantVersion.version_number.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_versions(self, variant_id: int, limit: int = 10) -> list[VariantVersion]:
        """Return all saved versions for a variant."""
        stmt = (
            select(VariantVersion)
            .where(VariantVersion.variant_id == variant_id)
            .order_by(VariantVersion.version_number.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def name_exists(self, campaign_id: int, name: str, exclude_variant_id: int | None = None) -> bool:
        """Check whether a variant name already exists in the campaign."""
        stmt = select(func.count(Variant.id)).where(
            Variant.campaign_id == campaign_id,
            func.lower(Variant.name) == name.strip().lower(),
        )
        if exclude_variant_id is not None:
            stmt = stmt.where(Variant.id != exclude_variant_id)
        count = self.db.scalar(stmt) or 0
        return count > 0
