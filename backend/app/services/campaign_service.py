"""Service-layer module for campaign service.
Implements business rules and orchestration for this domain area.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.enums import CreatedBySystem, VariantSource
from app.models.user import User
from app.models.variant import Variant
from app.models.variant_version import VariantVersion
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.assets import CampaignAssets
from app.schemas.campaign import CampaignCreateRequest


class CampaignService:
    """Service layer for campaign workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.variant_repo = VariantRepository(db)

    def create_campaign(self, user: User, payload: CampaignCreateRequest) -> Campaign:
        """Create and persist campaign."""
        base_constraints = dict(payload.constraints_json or {})
        campaign = Campaign(
            user_id=user.id,
            name=payload.name,
            product_title=payload.product_title,
            product_category=payload.product_category,
            product_description=payload.product_description,
            objective=payload.objective,
            audience_segment=payload.audience_segment,
            constraints_json=base_constraints,
            primary_kpi=payload.primary_kpi,
            status=payload.status,
        )
        self.campaign_repo.create(campaign)
        baseline_assets = CampaignAssets(
            hero={
                "headline": f"{payload.product_title} for {payload.product_category} shoppers",
                "subheadline": f"Designed for {payload.audience_segment} with measurable lift potential.",
                "cta_text": "Shop Now",
                "trust_callout": "Free shipping, 1-year warranty, and hassle-free returns",
            },
            bullets=[
                "Fast setup and easy purchase flow",
                "Trusted by thousands of repeat customers",
                "Tailored messaging for campaign objective",
            ],
            banner={"text": "Limited-time offer for this campaign", "badge": "Launch"},
            meta={"strategy_tag": "baseline", "rationale": "baseline:default"},
        )
        variant = Variant(
            campaign_id=campaign.id,
            name="Variant A",
            strategy_tag="baseline",
            assets_json=baseline_assets.model_dump(),
            source=VariantSource.HUMAN,
        )
        self.variant_repo.create(variant)
        self.variant_repo.create_version(
            VariantVersion(
                variant_id=variant.id,
                version_number=1,
                assets_json=baseline_assets.model_dump(),
                parent_version_id=None,
                created_by_user_id=user.id,
                created_by_system=CreatedBySystem.USER,
                change_summary="Initial baseline landing page variant",
            )
        )
        constraints = dict(campaign.constraints_json or {})
        constraints.setdefault("baseline_variant_id", variant.id)
        constraints.setdefault("original_baseline_variant_id", variant.id)
        campaign.constraints_json = constraints
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def list_campaigns(self, user: User) -> list[Campaign]:
        """Return all campaigns owned by the authenticated user."""
        campaigns = self.campaign_repo.list_for_user(user.id)
        touched = False
        for campaign in campaigns:
            if self._ensure_baseline_constraints(campaign):
                touched = True
        if touched:
            self.db.commit()
            for campaign in campaigns:
                self.db.refresh(campaign)
        return campaigns

    def get_campaign(self, user: User, campaign_id: int) -> Campaign:
        """Return one campaign owned by the authenticated user."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user.id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        if self._ensure_baseline_constraints(campaign):
            self.db.commit()
            self.db.refresh(campaign)
        return campaign

    def delete_campaign(self, user: User, campaign_id: int) -> None:
        """Delete one campaign owned by the authenticated user."""
        deleted = self.campaign_repo.delete_for_user(campaign_id, user.id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        self.db.commit()

    def set_baseline_variant(
        self,
        user: User,
        campaign_id: int,
        variant_id: int,
        baseline_name: str | None = None,
    ) -> Campaign:
        """Set a specific variant as the campaign baseline."""
        campaign = self.get_campaign(user, campaign_id)
        variant = self.variant_repo.get(variant_id)
        if not variant or variant.campaign_id != campaign_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found for campaign")

        constraints = dict(campaign.constraints_json or {})
        previous_baseline_id = constraints.get("baseline_variant_id")
        if previous_baseline_id and int(previous_baseline_id) != variant_id:
            previous_baseline = self.variant_repo.get(int(previous_baseline_id))
            if (
                previous_baseline
                and previous_baseline.campaign_id == campaign_id
                and previous_baseline.name.strip().lower() == "baseline"
            ):
                previous_baseline.name = self._resolve_unique_variant_name(
                    campaign_id,
                    f"Variant {previous_baseline.id}",
                    exclude_variant_id=previous_baseline.id,
                )

        if baseline_name and baseline_name.strip():
            clean_name = baseline_name.strip()
            if self.variant_repo.name_exists(campaign_id, clean_name, exclude_variant_id=variant_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baseline name already exists")
            variant.name = clean_name

        constraints.setdefault("original_baseline_variant_id", constraints.get("baseline_variant_id", variant_id))
        constraints["baseline_variant_id"] = variant_id
        constraints["baseline_set_at"] = datetime.now(timezone.utc).isoformat()
        self._normalize_baseline_names(campaign_id, variant_id)
        campaign.constraints_json = constraints
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def revert_baseline_variant(self, user: User, campaign_id: int) -> Campaign:
        """Revert campaign baseline selection to the original variant."""
        campaign = self.get_campaign(user, campaign_id)
        constraints = dict(campaign.constraints_json or {})
        original_baseline_id = constraints.get("original_baseline_variant_id")
        if not original_baseline_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No original baseline recorded")
        variant = self.variant_repo.get(int(original_baseline_id))
        if not variant or variant.campaign_id != campaign_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original baseline variant not found")

        constraints["baseline_variant_id"] = int(original_baseline_id)
        self._normalize_baseline_names(campaign_id, int(original_baseline_id))
        campaign.constraints_json = constraints
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def _resolve_unique_variant_name(self, campaign_id: int, base_name: str, exclude_variant_id: int | None = None) -> str:
        """Build a unique variant name scoped to one campaign."""
        candidate = base_name.strip()
        if not self.variant_repo.name_exists(campaign_id, candidate, exclude_variant_id=exclude_variant_id):
            return candidate
        suffix = 2
        while True:
            next_candidate = f"{candidate} ({suffix})"
            if not self.variant_repo.name_exists(campaign_id, next_candidate, exclude_variant_id=exclude_variant_id):
                return next_candidate
            suffix += 1

    def _normalize_baseline_names(self, campaign_id: int, active_baseline_id: int) -> None:
        """Ensure only the active baseline variant keeps the reserved baseline name."""
        for variant in self.variant_repo.list_for_campaign(campaign_id):
            if variant.id == active_baseline_id:
                continue
            if variant.name.strip().lower() == "baseline":
                variant.name = self._resolve_unique_variant_name(
                    campaign_id,
                    f"Variant {variant.id}",
                    exclude_variant_id=variant.id,
                )

    def _ensure_baseline_constraints(self, campaign: Campaign) -> bool:
        """Backfill or repair baseline ids in campaign constraints for legacy rows."""
        variants = self.variant_repo.list_for_campaign(campaign.id)
        if not variants:
            return False
        constraints = dict(campaign.constraints_json or {})
        variant_ids = {variant.id for variant in variants}

        baseline_id_raw = constraints.get("baseline_variant_id")
        baseline_id = None
        if isinstance(baseline_id_raw, int):
            baseline_id = baseline_id_raw
        elif isinstance(baseline_id_raw, str) and baseline_id_raw.isdigit():
            baseline_id = int(baseline_id_raw)
        if baseline_id not in variant_ids:
            named_baseline = next((variant for variant in variants if variant.name.strip().lower() == "baseline"), None)
            baseline_id = named_baseline.id if named_baseline else variants[0].id

        original_id_raw = constraints.get("original_baseline_variant_id")
        original_id = None
        if isinstance(original_id_raw, int):
            original_id = original_id_raw
        elif isinstance(original_id_raw, str) and original_id_raw.isdigit():
            original_id = int(original_id_raw)
        if original_id not in variant_ids:
            original_id = baseline_id

        changed = False
        if constraints.get("baseline_variant_id") != baseline_id:
            constraints["baseline_variant_id"] = baseline_id
            changed = True
        if constraints.get("original_baseline_variant_id") != original_id:
            constraints["original_baseline_variant_id"] = original_id
            changed = True

        if changed:
            campaign.constraints_json = constraints
        return changed
