"""Service-layer module for variant service.
Implements business rules and orchestration for this domain area.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.enums import ActorType, CreatedBySystem, LiftEventType, VariantSource
from app.models.improvement_recommendation import ImprovementRecommendation
from app.models.lift_trace_event import LiftTraceEvent
from app.models.metric_snapshot import MetricSnapshot
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.variant import Variant
from app.models.variant_version import VariantVersion
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.patch import PatchDocument
from app.schemas.variant import ManualVariantEditRequest
from app.services.codex_service import CodexService
from app.services.codex_rate_limit_service import CodexRateLimitService
from app.services.lift_trace_service import LiftTraceService
from app.services.patch_apply_service import PatchApplyService


class VariantService:
    """Service layer for variant workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.variant_repo = VariantRepository(db)
        self.campaign_repo = CampaignRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.feedback_repo = FeedbackRepository(db)
        self.codex_service = CodexService()
        self.rate_limit_service = CodexRateLimitService()
        self.trace_service = LiftTraceService(db)
        self.patch_service = PatchApplyService()

    def list_variants(self, campaign_id: int) -> list[Variant]:
        """Return variants for a campaign visible to the current user."""
        return self.variant_repo.list_for_campaign(campaign_id)

    def delete_variant(self, variant_id: int, user: User) -> dict:
        """Delete a non-baseline variant and clean all dependent records."""
        variant = self.variant_repo.get(variant_id)
        if not variant:
            raise ValueError("Variant not found")
        campaign = self.campaign_repo.get_for_user(variant.campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        constraints = campaign.constraints_json or {}
        variants = self.variant_repo.list_for_campaign(campaign.id)
        variant_ids = {item.id for item in variants}
        baseline_variant_id_raw = constraints.get("baseline_variant_id")
        baseline_variant_id = None
        if isinstance(baseline_variant_id_raw, int):
            baseline_variant_id = baseline_variant_id_raw
        elif isinstance(baseline_variant_id_raw, str) and baseline_variant_id_raw.isdigit():
            baseline_variant_id = int(baseline_variant_id_raw)
        if baseline_variant_id not in variant_ids:
            named_baseline = next((item for item in variants if item.name.strip().lower() == "baseline"), None)
            baseline_variant_id = named_baseline.id if named_baseline else (variants[0].id if variants else None)
        original_baseline_variant_id_raw = constraints.get("original_baseline_variant_id")
        original_baseline_variant_id = None
        if isinstance(original_baseline_variant_id_raw, int):
            original_baseline_variant_id = original_baseline_variant_id_raw
        elif isinstance(original_baseline_variant_id_raw, str) and original_baseline_variant_id_raw.isdigit():
            original_baseline_variant_id = int(original_baseline_variant_id_raw)
        if original_baseline_variant_id not in variant_ids:
            original_baseline_variant_id = baseline_variant_id
        if baseline_variant_id == variant.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Baseline variant cannot be deleted")
        if original_baseline_variant_id == variant.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original baseline variant cannot be deleted",
            )

        recommendation_ids = list(
            self.db.scalars(
                select(ImprovementRecommendation.id).where(ImprovementRecommendation.variant_id == variant.id)
            ).all()
        )
        if recommendation_ids:
            self.db.execute(
                delete(RecommendationFeedback).where(RecommendationFeedback.recommendation_id.in_(recommendation_ids))
            )
            self.db.execute(delete(LiftTraceEvent).where(LiftTraceEvent.recommendation_id.in_(recommendation_ids)))

        self.db.execute(delete(RecommendationFeedback).where(RecommendationFeedback.variant_id == variant.id))
        self.db.execute(delete(LiftTraceEvent).where(LiftTraceEvent.variant_id == variant.id))
        self.db.execute(delete(ImprovementRecommendation).where(ImprovementRecommendation.variant_id == variant.id))
        self.db.execute(delete(MetricSnapshot).where(MetricSnapshot.variant_id == variant.id))
        self.db.execute(delete(VariantVersion).where(VariantVersion.variant_id == variant.id))
        self.variant_repo.delete(variant)
        self.db.commit()
        return {
            "ok": True,
            "variant_id": variant_id,
            "variant_name": variant.name,
            "message": "Variant deleted",
        }

    def generate_variants(self, campaign_id: int, user: User) -> list[Variant]:
        """Generate campaign variants using Codex or fallback logic."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")
        existing = self.variant_repo.list_for_campaign(campaign_id)
        if len(existing) >= 3:
            return existing[:3]
        self.rate_limit_service.check(user.id, "generate_variants")

        generated = self.codex_service.generate_variants(
            {
                "campaign_id": campaign.id,
                "name": campaign.name,
                "product_title": campaign.product_title,
                "product_category": campaign.product_category,
                "product_description": campaign.product_description,
                "audience_segment": campaign.audience_segment,
                "constraints_json": campaign.constraints_json,
            }
        )

        created: list[Variant] = []
        for i, generated_variant in enumerate(generated.variants[:3]):
            variant = Variant(
                campaign_id=campaign.id,
                name=f"Variant {chr(65 + i)}",
                strategy_tag=generated_variant.strategy_tag,
                assets_json=generated_variant.assets.model_dump(),
                source=VariantSource.CODEX_GENERATED,
            )
            self.variant_repo.create(variant)
            self.db.flush()
            version = VariantVersion(
                variant_id=variant.id,
                version_number=1,
                assets_json=variant.assets_json,
                parent_version_id=None,
                created_by_user_id=user.id,
                created_by_system=CreatedBySystem.CODEX,
                change_summary=f"Initial generated variant: {generated_variant.rationale}",
            )
            self.variant_repo.create_version(version)
            self.trace_service.log(
                campaign_id=campaign.id,
                variant_id=variant.id,
                event_type=LiftEventType.RECOMMENDATION_CREATED,
                summary=f"Variant {variant.name} generated by Codex",
                actor_type=ActorType.CODEX,
                actor_id=user.id,
                metadata_json={"rationale": generated_variant.rationale},
            )
            created.append(variant)

        self.db.commit()
        for variant in created:
            self.db.refresh(variant)
        return created

    def manual_edit_variant(self, variant_id: int, payload: ManualVariantEditRequest, user: User) -> Variant:
        """Execute manual edit variant."""
        variant = self.variant_repo.get(variant_id)
        if not variant:
            raise ValueError("Variant not found")
        campaign = self.campaign_repo.get_for_user(variant.campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        patch_doc = PatchDocument.model_validate(
            {
                "operations": [
                    {
                        "op": "replace",
                        "path": payload.path,
                        "value": payload.value,
                        "reason": payload.reason or "Manual edit from landing preview",
                    }
                ]
            }
        )
        patched_assets = self.patch_service.apply_patch(variant.assets_json, patch_doc)

        latest = self.variant_repo.latest_version(variant.id)
        next_version = self.variant_repo.next_version_number(variant.id)
        version = VariantVersion(
            variant_id=variant.id,
            version_number=next_version,
            assets_json=patched_assets,
            parent_version_id=latest.id if latest else None,
            created_by_user_id=user.id,
            created_by_system=CreatedBySystem.USER,
            change_summary=f"Manual edit: {payload.path}",
        )
        self.variant_repo.create_version(version)
        variant.assets_json = patched_assets
        variant.source = VariantSource.HUMAN
        if payload.variant_name and payload.variant_name.strip():
            variant.name = self._validated_unique_variant_name(
                variant.campaign_id,
                payload.variant_name.strip(),
                exclude_variant_id=variant.id,
            )
        self.trace_service.log(
            campaign_id=variant.campaign_id,
            variant_id=variant.id,
            event_type=LiftEventType.APPLIED,
            summary=f"Manual change applied to {payload.path}",
            actor_type=ActorType.USER,
            actor_id=user.id,
            metadata_json={"path": payload.path, "reason": payload.reason},
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def _resolve_unique_variant_name(self, campaign_id: int, base_name: str, exclude_variant_id: int | None = None) -> str:
        """Execute resolve unique variant name."""
        candidate = base_name.strip()
        if not self.variant_repo.name_exists(campaign_id, candidate, exclude_variant_id=exclude_variant_id):
            return candidate
        suffix = 2
        while True:
            next_candidate = f"{candidate} ({suffix})"
            if not self.variant_repo.name_exists(campaign_id, next_candidate, exclude_variant_id=exclude_variant_id):
                return next_candidate
            suffix += 1

    def _validated_unique_variant_name(
        self,
        campaign_id: int,
        candidate_name: str,
        exclude_variant_id: int | None = None,
    ) -> str:
        """Validate user-provided variant name and reject duplicates explicitly."""
        clean_name = candidate_name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Variant name is required")
        if clean_name.lower() == "baseline":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Baseline is reserved for the active baseline variant",
            )
        if self.variant_repo.name_exists(campaign_id, clean_name, exclude_variant_id=exclude_variant_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Variant name already exists")
        return clean_name

    def version_performance(self, variant_id: int, user: User) -> list[dict]:
        """Execute version performance."""
        variant = self.variant_repo.get(variant_id)
        if not variant:
            raise ValueError("Variant not found")
        campaign = self.campaign_repo.get_for_user(variant.campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        versions = list(reversed(self.variant_repo.list_versions(variant_id, limit=3)))
        snapshots = list(reversed(self.metrics_repo.list_for_campaign(variant.campaign_id, variant_id=variant_id)))
        sentiment = self.feedback_repo.sentiment_for_variant(variant.campaign_id, variant_id)
        sentiment_score = sentiment["positive_count"] - sentiment["negative_count"]

        output: list[dict] = []
        for idx, version in enumerate(versions):
            start = version.created_at
            end = versions[idx + 1].created_at if idx + 1 < len(versions) else None
            segment = [
                s
                for s in snapshots
                if s.timestamp >= start and (end is None or s.timestamp < end)
            ]
            if segment:
                avg_ctr = float(sum(float(s.ctr) for s in segment) / len(segment))
                avg_atc = float(sum(float(s.atc_rate) for s in segment) / len(segment))
                avg_bounce = float(sum(float(s.bounce_rate) for s in segment) / len(segment))
                spend = float(sum(int(s.add_to_cart) for s in segment) * 80)
            else:
                avg_ctr = None
                avg_atc = None
                avg_bounce = None
                spend = 0.0

            output.append(
                {
                    "version_id": version.id,
                    "version_number": version.version_number,
                    "created_at": version.created_at,
                    "avg_ctr": avg_ctr,
                    "avg_atc_rate": avg_atc,
                    "avg_bounce_rate": avg_bounce,
                    "estimated_spend": spend,
                    "sentiment_score": float(sentiment_score),
                }
            )
        return output

    def submit_for_admin_approval(self, variant_id: int, user: User) -> dict:
        """Submit a variant for simulated admin approval with server-side status tracking."""
        variant = self.variant_repo.get(variant_id)
        if not variant:
            raise ValueError("Variant not found")
        campaign = self.campaign_repo.get_for_user(variant.campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        approval_state = self.admin_approval_status(variant_id, user)
        if approval_state["status"] == "APPROVED":
            return {
                "ok": True,
                "variant_id": variant.id,
                "variant_name": variant.name,
                "status": "APPROVED",
                "message": "Already approved by website admin.",
            }
        if approval_state["status"] == "PENDING_ADMIN_APPROVAL":
            seconds_elapsed = int(approval_state.get("seconds_since_submission") or 0)
            if seconds_elapsed < 5:
                return {
                    "ok": True,
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "status": "PENDING_ADMIN_APPROVAL",
                    "message": "Already sent for approval. Please wait a few seconds.",
                }
            return {
                "ok": True,
                "variant_id": variant.id,
                "variant_name": variant.name,
                "status": "PENDING_ADMIN_APPROVAL",
                "message": "This variant is still pending website admin approval.",
            }

        self.trace_service.log(
            campaign_id=variant.campaign_id,
            variant_id=variant.id,
            event_type=LiftEventType.APPROVED,
            summary=f"Variant '{variant.name}' submitted for website admin approval",
            actor_type=ActorType.USER,
            actor_id=user.id,
            metadata_json={
                "workflow_stage": "ADMIN_APPROVAL_SUBMITTED",
                "variant_name": variant.name,
            },
        )
        self.db.commit()
        return {
            "ok": True,
            "variant_id": variant.id,
            "variant_name": variant.name,
            "status": "PENDING_ADMIN_APPROVAL",
            "message": "Submitted for website admin approval.",
        }

    def admin_approval_status(self, variant_id: int, user: User) -> dict:
        """Return current simulated admin-approval status for a variant."""
        variant = self.variant_repo.get(variant_id)
        if not variant:
            raise ValueError("Variant not found")
        campaign = self.campaign_repo.get_for_user(variant.campaign_id, user.id)
        if not campaign:
            raise ValueError("Campaign not found")

        events = self.trace_service.repo.list_for_variant(campaign.id, variant.id, limit=50)
        submitted_event = next(
            (
                event
                for event in events
                if event.metadata_json and event.metadata_json.get("workflow_stage") == "ADMIN_APPROVAL_SUBMITTED"
            ),
            None,
        )
        approved_event = next(
            (
                event
                for event in events
                if event.metadata_json and event.metadata_json.get("workflow_stage") == "ADMIN_APPROVAL_APPROVED"
            ),
            None,
        )

        if not submitted_event:
            return {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "status": "NOT_SUBMITTED",
                "message": "Not yet submitted for admin approval.",
                "seconds_since_submission": None,
                "seconds_until_auto_approval": None,
            }

        submitted_at = submitted_event.created_at
        now = datetime.now(timezone.utc)
        submitted_at_utc = submitted_at if submitted_at.tzinfo else submitted_at.replace(tzinfo=timezone.utc)
        elapsed = max(0, int((now - submitted_at_utc).total_seconds()))

        if approved_event and approved_event.created_at >= submitted_event.created_at:
            return {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "status": "APPROVED",
                "message": "Approved by website admin.",
                "seconds_since_submission": elapsed,
                "seconds_until_auto_approval": 0,
            }

        if elapsed >= 10:
            self.trace_service.log(
                campaign_id=campaign.id,
                variant_id=variant.id,
                event_type=LiftEventType.APPROVED,
                summary=f"Variant '{variant.name}' approved by website admin",
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                metadata_json={
                    "workflow_stage": "ADMIN_APPROVAL_APPROVED",
                    "variant_name": variant.name,
                },
            )
            self.db.commit()
            return {
                "variant_id": variant.id,
                "variant_name": variant.name,
                "status": "APPROVED",
                "message": "Approved by website admin.",
                "seconds_since_submission": elapsed,
                "seconds_until_auto_approval": 0,
            }

        return {
            "variant_id": variant.id,
            "variant_name": variant.name,
            "status": "PENDING_ADMIN_APPROVAL",
            "message": "Pending website admin approval.",
            "seconds_since_submission": elapsed,
            "seconds_until_auto_approval": max(0, 10 - elapsed),
        }
