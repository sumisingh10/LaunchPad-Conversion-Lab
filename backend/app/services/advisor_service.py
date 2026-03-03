"""Service-layer module for advisor service.
Implements business rules and orchestration for this domain area.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.variant_repository import VariantRepository
from app.services.codex_service import CodexService


class AdvisorService:
    """Service layer for advisor workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.variant_repo = VariantRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.codex_service = CodexService()

    def advise(self, campaign_id: int, user: User, user_goal: str, variant_ids: list[int] | None = None) -> dict:
        """Select the strongest variant for the optimization goal."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        variants = self.variant_repo.list_for_campaign(campaign_id)
        if variant_ids:
            allow = set(variant_ids)
            variants = [v for v in variants if v.id in allow]
        if not variants:
            raise ValueError("No variants available for advice")

        metrics = []
        for variant in variants:
            latest = self.metrics_repo.latest_for_variant(campaign_id, variant.id)
            metrics.append(
                {
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "strategy_tag": variant.strategy_tag,
                    "ctr": float(latest.ctr) if latest else None,
                    "atc_rate": float(latest.atc_rate) if latest else None,
                    "bounce_rate": float(latest.bounce_rate) if latest else None,
                }
            )

        advice = self.codex_service.advise_best_variant(
            {
                "campaign_id": campaign_id,
                "objective": campaign.objective.value,
                "user_goal": user_goal,
                "variants": metrics,
            }
        ).model_dump()

        allowed_ids = {variant.id for variant in variants}
        if advice["best_variant_id"] not in allowed_ids:
            fallback_choice = variants[0]
            advice["best_variant_id"] = fallback_choice.id
            advice["best_variant_name"] = fallback_choice.name
            advice["rationale"] = (
                f"{advice['rationale']} Mapped to visible set: selected {fallback_choice.name}."
            )
            return advice

        if not advice.get("best_variant_name"):
            selected = next((variant for variant in variants if variant.id == advice["best_variant_id"]), None)
            advice["best_variant_name"] = selected.name if selected else None
        return advice
