"""Service-layer module for recommendation service.
Implements business rules and orchestration for this domain area.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ActorType, CreatedBySystem, LiftEventType, RecommendationStatus, VariantSource
from app.models.improvement_recommendation import ImprovementRecommendation
from app.models.user import User
from app.models.variant import Variant
from app.models.variant_version import VariantVersion
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.patch import PatchDocument
from app.services.change_policy_service import ChangePolicyService
from app.services.codex_service import CodexService
from app.services.codex_rate_limit_service import CodexRateLimitService
from app.services.diagnostics_service import DiagnosticsService
from app.services.guardrail_service import GuardrailService
from app.services.lift_trace_service import LiftTraceService
from app.services.org_memory_service import OrgMemoryService
from app.services.patch_apply_service import PatchApplyService


class RecommendationService:
    """Service layer for recommendation workflows."""
    def __init__(self, db: Session):
        """Initialize service dependencies for the current request scope."""
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.variant_repo = VariantRepository(db)
        self.reco_repo = RecommendationRepository(db)
        self.feedback_repo = FeedbackRepository(db)
        self.diagnostics_service = DiagnosticsService()
        self.change_policy_service = ChangePolicyService()
        self.codex_service = CodexService()
        self.rate_limit_service = CodexRateLimitService()
        self.patch_service = PatchApplyService()
        self.guardrail_service = GuardrailService()
        self.org_memory_service = OrgMemoryService()
        self.trace = LiftTraceService(db)

    def analyze_kpis(self, campaign_id: int, user: User) -> list[dict]:
        """Analyze and return kpis."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user.id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        snapshots = self.metrics_repo.list_for_campaign(campaign_id)
        return self.diagnostics_service.analyze(snapshots)

    def propose_improvements(
        self,
        campaign_id: int,
        user: User,
        user_goal: str | None = None,
        landing_page_snapshot_url: str | None = None,
        focus_component: str | None = None,
        selected_variant_id: int | None = None,
    ):
        """Propose and return improvements."""
        campaign = self.campaign_repo.get_for_user(campaign_id, user.id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        self.rate_limit_service.check(user.id, "propose_improvements")

        # Keep previously saved recommendations visible, but replace stale pending proposals.
        for old in self.reco_repo.list_for_campaign(campaign_id):
            if old.status == RecommendationStatus.PROPOSED:
                old.status = RecommendationStatus.REJECTED

        snapshots = self.metrics_repo.list_for_campaign(campaign_id)
        findings = self.diagnostics_service.analyze(snapshots)
        interventions = self.change_policy_service.map_findings_to_interventions(findings)
        feedback_by_recommendation = self.feedback_repo.summary_for_campaign(campaign_id)
        feedback_by_change_type = self.feedback_repo.summary_by_change_type_for_campaign(campaign_id)
        feedback_by_change_type_map = {item["change_type"]: item for item in feedback_by_change_type}
        org_memory = self.org_memory_service.insights_for_objective(campaign.objective.value)

        variants = self.variant_repo.list_for_campaign(campaign_id)
        if selected_variant_id is not None:
            variants = [item for item in variants if item.id == selected_variant_id]
            if not variants:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected variant not found")
        created = []
        used_change_types: set[str] = set()
        for variant in variants:
            variant_interventions = [i for i in interventions if i["variant_id"] == variant.id]
            if not variant_interventions:
                variant_interventions = [
                    {
                        "variant_id": variant.id,
                        "change_type": "COPY",
                        "target_component": "hero.subheadline",
                        "intent": "Generate at least one actionable copy test from current KPI context",
                    }
                ]
            variant_interventions = self._augment_interventions(variant.id, variant_interventions, user_goal, focus_component)
            latest_snapshot = self.metrics_repo.latest_for_variant(campaign_id, variant.id)
            visual_context = self._build_visual_context(variant.assets_json)
            selected_area_context = self._build_selected_area_context(variant.assets_json, focus_component)
            snapshot_url = landing_page_snapshot_url
            if isinstance(campaign.constraints_json, dict):
                snapshot_url = snapshot_url or campaign.constraints_json.get("landing_page_snapshot_url")
            codex_response = self.codex_service.propose_improvements(
                {
                    "campaign_id": campaign_id,
                    "variant_id": variant.id,
                    "campaign": {
                        "name": campaign.name,
                        "objective": campaign.objective.value,
                        "constraints": campaign.constraints_json,
                    },
                    "assets": variant.assets_json,
                    "visual_context": visual_context,
                    "selected_area_context": selected_area_context,
                    "landing_page_snapshot_url": snapshot_url,
                    "findings": findings,
                    "interventions": variant_interventions,
                    "lift_trace": [e.summary for e in self.trace.list_events(campaign_id)[:5]],
                    "feedback_summary": {
                        "by_recommendation": feedback_by_recommendation,
                        "by_change_type": feedback_by_change_type,
                    },
                    "org_memory": org_memory,
                    "operator_goal": user_goal,
                    "focus_component": focus_component,
                    "latest_metrics": {
                        "ctr": float(latest_snapshot.ctr) if latest_snapshot else None,
                        "atc_rate": float(latest_snapshot.atc_rate) if latest_snapshot else None,
                        "bounce_rate": float(latest_snapshot.bounce_rate) if latest_snapshot else None,
                    },
                }
            )

            candidates: list[tuple[int, dict, any]] = []
            for rec in codex_response.recommendations:
                validated_patch = self.codex_service.validate_patch_json(rec.patch.model_dump())
                patch_doc = PatchDocument.model_validate(validated_patch)
                guardrail = self.guardrail_service.assess_patch(variant.assets_json, patch_doc, campaign.constraints_json)
                if not guardrail.allowed:
                    self.trace.log(
                        campaign_id=campaign_id,
                        variant_id=variant.id,
                        event_type=LiftEventType.OUTCOME_RECORDED,
                        summary=f"Guardrail blocked recommendation for variant {variant.name}",
                        actor_type=ActorType.SYSTEM,
                        actor_id=None,
                        metadata_json={
                            "blocked_patch": validated_patch,
                            "violations": guardrail.violations,
                            "risk_level": guardrail.risk_level,
                        },
                    )
                    continue

                base_score = self.guardrail_service.recommendation_score(
                    rank=rec.rank,
                    risk_level=guardrail.risk_level,
                    has_metrics=latest_snapshot is not None,
                )
                feedback_signal = feedback_by_change_type_map.get(rec.change_type.value)
                feedback_bonus = self._feedback_bonus(feedback_signal)
                adjusted_score = max(0, min(100, base_score + feedback_bonus))
                expected_impact = dict(rec.expected_impact_json)
                expected_impact["guardrail"] = {
                    "risk_level": guardrail.risk_level,
                    "operations_count": guardrail.operations_count,
                    "violations": guardrail.violations,
                }
                expected_impact["priority_score"] = base_score
                expected_impact["feedback_bonus"] = feedback_bonus
                expected_impact["adjusted_priority_score"] = adjusted_score
                expected_impact["learning_signal"] = feedback_signal
                candidates.append((adjusted_score, expected_impact, rec))

            candidates.sort(key=lambda item: item[0], reverse=True)
            if focus_component:
                focus_norm = focus_component.strip().lower()

                def _matches_selected_focus(rec) -> bool:
                    """Execute matches selected focus."""
                    target = str(rec.target_component).strip().lower()
                    if target == focus_norm:
                        return True
                    if focus_norm == "bullets" and target.startswith("bullets"):
                        return True
                    if "layout" in focus_norm or "image" in focus_norm or focus_norm == "product image block":
                        return any(op.path == "meta.rationale" for op in rec.patch.operations)
                    return any(op.path == focus_norm for op in rec.patch.operations)

                focus_candidates = [
                    item
                    for item in candidates
                    if _matches_selected_focus(item[2])
                ]
                selected_candidates = focus_candidates or candidates
                for _, expected_impact, rec in selected_candidates[:3]:
                    new_rank = len(created) + 1
                    if new_rank > 3:
                        break
                    recommendation = ImprovementRecommendation(
                        campaign_id=campaign_id,
                        variant_id=variant.id,
                        status=RecommendationStatus.PROPOSED,
                        rank=new_rank,
                        change_type=rec.change_type,
                        target_component=rec.target_component,
                        rationale=rec.rationale,
                        hypothesis=rec.hypothesis,
                        expected_impact_json=expected_impact,
                        trigger_metrics_snapshot_id=latest_snapshot.id if latest_snapshot else None,
                        patch_json=self.codex_service.validate_patch_json(rec.patch.model_dump()),
                        codex_raw_response_json=rec.model_dump(),
                    )
                    self.reco_repo.create(recommendation)
                    self.trace.log(
                        campaign_id=campaign_id,
                        variant_id=variant.id,
                        recommendation_id=recommendation.id,
                        event_type=LiftEventType.RECOMMENDATION_CREATED,
                        summary=f"Recommendation created for variant {variant.name}",
                        actor_type=ActorType.CODEX,
                        actor_id=user.id,
                        metadata_json={
                            "adjusted_priority_score": expected_impact.get("adjusted_priority_score"),
                            "feedback_bonus": expected_impact.get("feedback_bonus"),
                        },
                    )
                    created.append(recommendation)
                if len(created) >= 3:
                    break
                continue

            chosen = None
            for _, expected_impact, rec in candidates:
                if focus_component and rec.target_component == focus_component:
                    chosen = (expected_impact, rec)
                    break
                if rec.change_type.value not in used_change_types:
                    chosen = (expected_impact, rec)
                    break
            if chosen is None and candidates:
                chosen = (candidates[0][1], candidates[0][2])
            if chosen is None:
                continue
            expected_impact, rec = chosen
            used_change_types.add(rec.change_type.value)
            new_rank = len(created) + 1
            if new_rank > 3:
                break
            recommendation = ImprovementRecommendation(
                campaign_id=campaign_id,
                variant_id=variant.id,
                status=RecommendationStatus.PROPOSED,
                rank=new_rank,
                change_type=rec.change_type,
                target_component=rec.target_component,
                rationale=rec.rationale,
                hypothesis=rec.hypothesis,
                expected_impact_json=expected_impact,
                trigger_metrics_snapshot_id=latest_snapshot.id if latest_snapshot else None,
                patch_json=self.codex_service.validate_patch_json(rec.patch.model_dump()),
                codex_raw_response_json=rec.model_dump(),
            )
            self.reco_repo.create(recommendation)
            self.trace.log(
                campaign_id=campaign_id,
                variant_id=variant.id,
                recommendation_id=recommendation.id,
                event_type=LiftEventType.RECOMMENDATION_CREATED,
                summary=f"Recommendation created for variant {variant.name}",
                actor_type=ActorType.CODEX,
                actor_id=user.id,
                metadata_json={
                    "adjusted_priority_score": expected_impact.get("adjusted_priority_score"),
                    "feedback_bonus": expected_impact.get("feedback_bonus"),
                },
            )
            created.append(recommendation)
            if len(created) >= 3:
                break
        if len(created) > 3:
            created = created[:3]
        self.db.commit()
        return created

    def list_recommendations(self, campaign_id: int):
        """Return recommendations for a campaign."""
        return self.reco_repo.list_for_campaign(campaign_id)

    def auto_optimize(self, campaign_id: int, user: User, user_goal: str, preferred_variant_id: int | None = None):
        """Apply one automated optimization recommendation for compare flow."""
        proposed = self.propose_improvements(campaign_id, user, user_goal=user_goal)
        if not proposed:
            raise HTTPException(status_code=400, detail="No applicable recommendations produced")

        candidate = None
        if preferred_variant_id:
            for rec in proposed:
                if rec.variant_id == preferred_variant_id:
                    candidate = rec
                    break
        if candidate is None:
            candidate = proposed[0]

        self.approve(candidate.id, user)
        applied = self.apply(candidate.id, user)
        return {
            "applied_recommendation_id": applied.id,
            "variant_id": applied.variant_id,
            "status": applied.status.value,
        }

    def approve(self, recommendation_id: int, user: User):
        """Mark a recommendation as approved."""
        reco = self._get_recommendation(recommendation_id)
        reco.status = RecommendationStatus.APPROVED
        self.trace.log(
            campaign_id=reco.campaign_id,
            variant_id=reco.variant_id,
            recommendation_id=reco.id,
            event_type=LiftEventType.APPROVED,
            summary="Recommendation approved",
            actor_type=ActorType.USER,
            actor_id=user.id,
        )
        self.db.commit()
        self.db.refresh(reco)
        return reco

    def reject(self, recommendation_id: int, user: User):
        """Mark a recommendation as rejected."""
        reco = self._get_recommendation(recommendation_id)
        reco.status = RecommendationStatus.REJECTED
        self.trace.log(
            campaign_id=reco.campaign_id,
            variant_id=reco.variant_id,
            recommendation_id=reco.id,
            event_type=LiftEventType.REJECTED,
            summary="Recommendation rejected",
            actor_type=ActorType.USER,
            actor_id=user.id,
        )
        self.db.commit()
        self.db.refresh(reco)
        return reco

    def apply(self, recommendation_id: int, user: User, variant_name: str | None = None):
        """Apply recommendation patch to the target variant."""
        reco = self._get_recommendation(recommendation_id)
        if reco.status not in (RecommendationStatus.APPROVED, RecommendationStatus.PROPOSED):
            raise HTTPException(status_code=400, detail="Recommendation is not applyable")

        variant = self.variant_repo.get(reco.variant_id)
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")

        patch = PatchDocument.model_validate(reco.patch_json)
        before_assets = variant.assets_json
        patched_assets = self.patch_service.apply_patch(before_assets, patch)

        latest = self.variant_repo.latest_version(variant.id)
        next_version = self.variant_repo.next_version_number(variant.id)
        version = VariantVersion(
            variant_id=variant.id,
            version_number=next_version,
            assets_json=patched_assets,
            parent_version_id=latest.id if latest else None,
            created_by_user_id=user.id,
            created_by_system=CreatedBySystem.CODEX,
            change_summary=f"Applied recommendation #{reco.id}: {reco.rationale[:120]}",
        )
        self.variant_repo.create_version(version)

        variant.assets_json = patched_assets
        variant.source = VariantSource.CODEX_PATCHED
        if variant_name and variant_name.strip():
            variant.name = self._validate_user_variant_name(
                variant.campaign_id,
                variant_name.strip(),
                exclude_variant_id=variant.id,
            )

        reco.status = RecommendationStatus.APPLIED
        self.trace.log(
            campaign_id=reco.campaign_id,
            variant_id=reco.variant_id,
            recommendation_id=reco.id,
            event_type=LiftEventType.APPLIED,
            summary="Recommendation patch applied",
            actor_type=ActorType.USER,
            actor_id=user.id,
            metadata_json={"patch": reco.patch_json},
        )

        self.db.commit()
        self.db.refresh(reco)
        return reco

    def save_as_variant(self, recommendation_id: int, user: User, variant_name: str | None = None) -> Variant:
        """Save and return as variant."""
        reco = self._get_recommendation(recommendation_id)
        base_variant = self.variant_repo.get(reco.variant_id)
        if not base_variant:
            raise HTTPException(status_code=404, detail="Variant not found")

        patch = PatchDocument.model_validate(reco.patch_json)
        patched_assets = self.patch_service.apply_patch(base_variant.assets_json, patch)

        sibling_count = len(self.variant_repo.list_for_campaign(base_variant.campaign_id))
        if variant_name and variant_name.strip():
            name = self._validate_user_variant_name(base_variant.campaign_id, variant_name.strip())
        else:
            requested_name = f"Variant {chr(65 + min(sibling_count, 25))}"
            name = self._resolve_unique_variant_name(base_variant.campaign_id, requested_name)
        new_variant = Variant(
            campaign_id=base_variant.campaign_id,
            name=name,
            strategy_tag=base_variant.strategy_tag,
            assets_json=patched_assets,
            source=VariantSource.CODEX_PATCHED,
        )
        self.variant_repo.create(new_variant)
        self.variant_repo.create_version(
            VariantVersion(
                variant_id=new_variant.id,
                version_number=1,
                assets_json=patched_assets,
                parent_version_id=None,
                created_by_user_id=user.id,
                created_by_system=CreatedBySystem.CODEX,
                change_summary=f"Saved from recommendation #{reco.id}",
            )
        )

        reco.status = RecommendationStatus.APPLIED
        self.trace.log(
            campaign_id=reco.campaign_id,
            variant_id=new_variant.id,
            recommendation_id=reco.id,
            event_type=LiftEventType.APPLIED,
            summary=f"Saved new variant '{new_variant.name}' from recommendation",
            actor_type=ActorType.USER,
            actor_id=user.id,
        )
        self.db.commit()
        self.db.refresh(new_variant)
        return new_variant

    def _get_recommendation(self, recommendation_id: int) -> ImprovementRecommendation:
        """Execute get recommendation."""
        recommendation = self.reco_repo.get(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return recommendation

    @staticmethod
    def _feedback_bonus(feedback_signal: dict | None) -> int:
        """Compute score bonus from historical feedback signals."""
        if not feedback_signal:
            return 0
        positive = int(feedback_signal.get("positive_count", 0))
        negative = int(feedback_signal.get("negative_count", 0))
        total = positive + negative
        if total == 0:
            return 0
        ratio = (positive - negative) / total
        return int(ratio * 12)

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

    def _validate_user_variant_name(
        self,
        campaign_id: int,
        candidate_name: str,
        exclude_variant_id: int | None = None,
    ) -> str:
        """Validate a user-provided variant name and fail on duplicates."""
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

    @staticmethod
    def _build_visual_context(assets: dict) -> dict:
        """Build textual storefront context from variant assets."""
        hero = assets.get("hero", {}) if isinstance(assets, dict) else {}
        banner = assets.get("banner", {}) if isinstance(assets, dict) else {}
        bullets = assets.get("bullets", []) if isinstance(assets, dict) else []
        return {
            "hero_headline": hero.get("headline"),
            "hero_subheadline": hero.get("subheadline"),
            "cta_text": hero.get("cta_text"),
            "trust_callout": hero.get("trust_callout"),
            "banner_text": banner.get("text"),
            "bullet_points": bullets,
        }

    @staticmethod
    def _build_selected_area_context(assets: dict, focus_component: str | None) -> dict | None:
        """Build focused context for selected storefront area."""
        focus = (focus_component or "").strip().lower()
        if not focus or not isinstance(assets, dict):
            return None

        hero = assets.get("hero", {}) if isinstance(assets.get("hero"), dict) else {}
        banner = assets.get("banner", {}) if isinstance(assets.get("banner"), dict) else {}
        bullets = assets.get("bullets", []) if isinstance(assets.get("bullets"), list) else []

        mapping = {
            "hero.headline": ("Hero Headline", hero.get("headline"), ["hero.headline"]),
            "hero.subheadline": ("Hero Subheadline", hero.get("subheadline"), ["hero.subheadline"]),
            "hero.cta_text": ("Primary CTA", hero.get("cta_text"), ["hero.cta_text"]),
            "hero.trust_callout": ("Trust Callout", hero.get("trust_callout"), ["hero.trust_callout"]),
            "banner.text": ("Promo Banner", banner.get("text"), ["banner.text"]),
            "banner.badge": ("Promo Badge", banner.get("badge"), ["banner.badge"]),
            "bullets": ("Benefits Grid", bullets, ["bullets.0", "bullets.1", "bullets.2"]),
        }

        if focus in mapping:
            label, current_value, allowed_paths = mapping[focus]
            return {
                "focus_component": focus_component,
                "focus_label": label,
                "current_value": current_value,
                "allowed_patch_paths": allowed_paths,
            }

        if focus.startswith("bullets."):
            index = 0
            try:
                index = max(0, min(2, int(focus.split(".", 1)[1])))
            except (ValueError, IndexError):
                index = 0
            value = bullets[index] if index < len(bullets) else None
            return {
                "focus_component": focus_component,
                "focus_label": f"Benefits Grid ({index + 1})",
                "current_value": value,
                "allowed_patch_paths": [f"bullets.{index}"],
            }

        if "image" in focus or "layout" in focus:
            return {
                "focus_component": focus_component,
                "focus_label": "Product Image Block / Layout",
                "current_value": "current storefront layout",
                "allowed_patch_paths": ["meta.rationale"],
            }
        return {
            "focus_component": focus_component,
            "focus_label": focus_component,
            "current_value": None,
            "allowed_patch_paths": [],
        }

    @staticmethod
    def _augment_interventions(
        variant_id: int,
        interventions: list[dict],
        user_goal: str | None,
        focus_component: str | None,
    ) -> list[dict]:
        """Expand intervention candidates based on user focus and goal."""
        output = list(interventions)
        goal = (user_goal or "").lower()
        focus = (focus_component or "").lower()
        existing_change_types = {item.get("change_type") for item in output}

        if "layout" in goal or "image" in goal or "layout" in focus or "image" in focus:
            if "LAYOUT" not in existing_change_types:
                output.append(
                    {
                        "variant_id": variant_id,
                        "change_type": "LAYOUT",
                        "target_component": "product image block",
                        "intent": "Rebalance image and hero order for scan speed and lower drop-off",
                    }
                )

        if "cta" in goal or "click" in goal:
            if "CTA" not in existing_change_types:
                output.append(
                    {
                        "variant_id": variant_id,
                        "change_type": "CTA",
                        "target_component": "hero.cta_text",
                        "intent": "Increase click intent with clearer action phrase",
                    }
                )

        if focus:
            output.append(
                {
                    "variant_id": variant_id,
                    "change_type": "COPY",
                    "target_component": focus_component,
                    "intent": f"Prioritize optimization on selected area: {focus_component}",
                }
            )
        return output
