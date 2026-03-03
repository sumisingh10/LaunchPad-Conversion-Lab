"""Service-layer module for codex service.
Implements business rules and orchestration for this domain area.
"""
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from random import Random
from tempfile import NamedTemporaryFile
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.advisor import VariantAdviceResponse
from app.schemas.assets import CampaignAssets
from app.schemas.codex import CodexVariantGenerationResponse, GeneratedVariant
from app.schemas.patch import ALLOWED_PATHS, PatchDocument
from app.schemas.recommendation import CodexImprovementRecommendation, CodexRecommendationResponse

logger = logging.getLogger(__name__)
_REQUEST_SEMAPHORE = threading.BoundedSemaphore(value=max(1, settings.codex_max_concurrent_requests))


class CodexService:
    """Service layer for codex workflows."""
    def __init__(self):
        """Initialize service dependencies for the current request scope."""
        self.provider = (settings.codex_provider or "api").lower()
        self.api_key = self._load_api_key()
        self.use_fallback = settings.codex_use_fallback

    def _raise_if_live_mode(self, operation: str, exc: Exception) -> None:
        """Raise a hard failure when live mode disables fallback behavior."""
        if self.provider == "cli":
            logger.warning("Codex CLI %s failed; falling back to deterministic generator: %s", operation, exc)
            return
        if not self.use_fallback:
            raise ValueError(f"Live Codex {operation} failed: {exc}") from exc

    @staticmethod
    def _load_api_key() -> str | None:
        """Load API key from direct value, file, or encrypted value."""
        if settings.codex_api_key:
            return settings.codex_api_key.strip()
        if settings.codex_api_key_file:
            try:
                with open(settings.codex_api_key_file, "r", encoding="utf-8") as f:
                    value = f.read().strip()
                    return value or None
            except FileNotFoundError:
                logger.warning("Configured CODEX_API_KEY_FILE was not found: %s", settings.codex_api_key_file)
        decryption_key = settings.codex_api_key_decryption_key
        if not decryption_key and settings.codex_api_key_decryption_key_file:
            try:
                with open(settings.codex_api_key_decryption_key_file, "r", encoding="utf-8") as f:
                    decryption_key = f.read().strip()
            except FileNotFoundError:
                logger.warning(
                    "Configured CODEX_API_KEY_DECRYPTION_KEY_FILE was not found: %s",
                    settings.codex_api_key_decryption_key_file,
                )
        if settings.codex_api_key_encrypted and decryption_key:
            try:
                decrypted = Fernet(decryption_key.encode("utf-8")).decrypt(
                    settings.codex_api_key_encrypted.encode("utf-8")
                )
                value = decrypted.decode("utf-8").strip()
                return value or None
            except (InvalidToken, ValueError):
                logger.warning("Unable to decrypt CODEX_API_KEY_ENCRYPTED with provided decryption key")
        return None

    @staticmethod
    def _should_retry(status_code: int) -> bool:
        """Return whether a failed request should be retried."""
        return status_code == 429 or 500 <= status_code < 600

    def _call_openai_json(self, system_prompt: str, user_payload: dict[str, Any], schema_name: str, schema: dict) -> dict:
        """Call OpenAI Responses API and parse strict JSON output."""
        if self.provider == "cli":
            return self._call_codex_cli_json(system_prompt, user_payload, schema_name, schema)

        if not self.api_key:
            raise ValueError("Missing CODEX_API_KEY")

        payload_copy = dict(user_payload)
        snapshot_url = payload_copy.get("landing_page_snapshot_url")
        user_content: Any
        if isinstance(snapshot_url, str) and snapshot_url.startswith(("http://", "https://", "data:image/")):
            payload_copy["landing_page_snapshot_url"] = "[attached_image]"
            user_content = [
                {"type": "input_text", "text": json.dumps(payload_copy)},
                {"type": "input_image", "image_url": snapshot_url},
            ]
        else:
            user_content = json.dumps(payload_copy)

        body = {
            "model": settings.codex_model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = None
        with _REQUEST_SEMAPHORE:
            with httpx.Client(timeout=45.0) as client:
                for attempt in range(settings.codex_max_retries):
                    response = client.post("https://api.openai.com/v1/responses", headers=headers, json=body)
                    if response.is_success:
                        data = response.json()
                        break

                    if attempt < settings.codex_max_retries - 1 and self._should_retry(response.status_code):
                        sleep_for = settings.codex_retry_base_seconds * (2**attempt)
                        logger.warning(
                            "Codex request retrying after status %s (attempt %s/%s)",
                            response.status_code,
                            attempt + 1,
                            settings.codex_max_retries,
                        )
                        time.sleep(sleep_for)
                        continue

                    response.raise_for_status()

        if data is None:
            raise ValueError("No response payload from Codex request")

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return json.loads(output_text)

        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return json.loads(content["text"])

        raise ValueError("No structured JSON content returned from model")

    def _call_codex_cli_json(self, system_prompt: str, user_payload: dict[str, Any], schema_name: str, schema: dict) -> dict:
        """Call `codex exec` and parse JSON response output."""
        cli_path = settings.codex_cli_path or "codex"
        resolved = shutil.which(cli_path) if os.path.sep not in cli_path else cli_path
        if not resolved:
            raise ValueError(f"codex CLI not found on PATH: {cli_path}")

        with NamedTemporaryFile("w", suffix=f"_{schema_name}.schema.json", delete=False) as schema_file:
            json.dump(schema, schema_file)
            schema_path = schema_file.name
        with NamedTemporaryFile("w+", suffix=f"_{schema_name}.out.json", delete=False) as output_file:
            output_path = output_file.name

        payload_copy = dict(user_payload)
        image_path: str | None = None
        snapshot_url = payload_copy.get("landing_page_snapshot_url")
        if isinstance(snapshot_url, str) and snapshot_url.startswith("data:image/"):
            try:
                header, encoded = snapshot_url.split(",", 1)
                mime_part = header.split(";")[0]
                extension = mime_part.split("/")[-1]
                image_bytes = json.loads(json.dumps(encoded))
                import base64

                decoded = base64.b64decode(image_bytes)
                with NamedTemporaryFile("wb", suffix=f".{extension}", delete=False) as image_file:
                    image_file.write(decoded)
                    image_path = image_file.name
                payload_copy["landing_page_snapshot_url"] = "[attached_image]"
            except Exception as exc:
                logger.warning("Failed to decode snapshot for codex exec image attachment: %s", exc)

        prompt = (
            f"{system_prompt}\n\n"
            "Return only JSON that matches the output schema.\n"
            f"Input payload:\n{json.dumps(payload_copy, ensure_ascii=True)}"
        )

        cmd = [
            resolved,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-C",
            os.getcwd(),
            "--output-schema",
            schema_path,
            "-o",
            output_path,
        ]
        if image_path:
            cmd.extend(["--image", image_path])
        cmd.append(
            prompt,
        )
        try:
            last_error: Exception | None = None
            for attempt in range(settings.codex_max_retries):
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=settings.codex_cli_timeout_seconds,
                    check=False,
                )
                if proc.returncode != 0:
                    last_error = ValueError(f"codex exec failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
                else:
                    with open(output_path, "r", encoding="utf-8") as f:
                        raw = f.read().strip()
                    if not raw:
                        last_error = ValueError("codex exec produced empty output")
                    else:
                        try:
                            return json.loads(raw)
                        except json.JSONDecodeError:
                            last_error = ValueError("codex exec produced invalid JSON")

                if attempt < settings.codex_max_retries - 1:
                    sleep_for = settings.codex_retry_base_seconds * (2**attempt)
                    logger.warning(
                        "Codex CLI request retrying after failed attempt %s/%s: %s",
                        attempt + 1,
                        settings.codex_max_retries,
                        last_error,
                    )
                    time.sleep(sleep_for)

            raise last_error or ValueError("codex exec failed")
        finally:
            cleanup_paths = [schema_path, output_path]
            if image_path:
                cleanup_paths.append(image_path)
            for path in cleanup_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _fallback_variants(self, campaign: dict) -> CodexVariantGenerationResponse:
        """Return deterministic fallback variants when live generation fails."""
        base_title = campaign["product_title"]
        category = campaign["product_category"]
        templates = [
            ("Variant A", "premium", "Premium positioning with trust-first framing"),
            ("Variant B", "value", "Value-forward positioning for price-sensitive segment"),
            ("Variant C", "urgency", "Urgency angle to boost immediate action"),
        ]
        out: list[GeneratedVariant] = []
        for name, tag, rationale in templates:
            assets = CampaignAssets(
                hero={
                    "headline": f"{base_title} for {category} shoppers",
                    "subheadline": f"Designed for {campaign['audience_segment']} with measurable lift potential.",
                    "cta_text": "Shop Now" if tag != "value" else "Get the Best Deal",
                    "trust_callout": "30-day returns and verified quality guarantee",
                },
                bullets=[
                    "Fast setup and easy purchase flow",
                    "Trusted by thousands of repeat customers",
                    "Tailored messaging for campaign objective",
                ],
                banner={"text": "Limited-time offer for this campaign", "badge": "Launch"},
                meta={"strategy_tag": tag, "rationale": rationale},
            )
            out.append(GeneratedVariant(name=name, strategy_tag=tag, rationale=rationale, assets=assets))
        return CodexVariantGenerationResponse(variants=out)

    def _variant_schema(self) -> dict:
        """Return JSON schema for variant generation responses."""
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "variants": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "strategy_tag": {"type": "string"},
                            "rationale": {"type": "string"},
                            "assets": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "hero": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "headline": {"type": "string"},
                                            "subheadline": {"type": "string"},
                                            "cta_text": {"type": "string"},
                                            "trust_callout": {"type": "string"},
                                        },
                                        "required": ["headline", "subheadline", "cta_text", "trust_callout"],
                                    },
                                    "bullets": {
                                        "type": "array",
                                        "minItems": 3,
                                        "maxItems": 3,
                                        "items": {"type": "string"},
                                    },
                                    "banner": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {"text": {"type": "string"}, "badge": {"type": ["string", "null"]}},
                                        "required": ["text", "badge"],
                                    },
                                    "meta": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "strategy_tag": {"type": "string"},
                                            "rationale": {"type": ["string", "null"]},
                                        },
                                        "required": ["strategy_tag", "rationale"],
                                    },
                                },
                                "required": ["hero", "bullets", "banner", "meta"],
                            },
                        },
                        "required": ["name", "strategy_tag", "rationale", "assets"],
                    },
                }
            },
            "required": ["variants"],
        }

    def generate_variants(self, campaign: dict) -> CodexVariantGenerationResponse:
        """Generate campaign variants using Codex or fallback logic."""
        system_prompt = (
            "You are an ecommerce experimentation assistant. Return only valid JSON matching the schema. "
            "Produce 2-3 strong variants with distinct strategies and concise high-conversion copy."
        )
        try:
            if self.provider != "cli" and not self.api_key:
                raise ValueError("Missing CODEX_API_KEY")
            raw = self._call_openai_json(system_prompt, campaign, "variant_generation", self._variant_schema())
            parsed = CodexVariantGenerationResponse.model_validate(raw)
            return parsed
        except Exception as exc:
            self._raise_if_live_mode("variant generation", exc)
            logger.warning("Codex live variant generation failed; using fallback: %s", exc)
            return self._fallback_variants(campaign)

    def _fallback_recommendations(self, inputs: dict[str, Any]) -> CodexRecommendationResponse:
        """Return deterministic fallback recommendations."""
        variant_id = int(inputs["variant_id"])
        goal = str(inputs.get("operator_goal") or "").lower()
        focus = str(inputs.get("focus_component") or "").lower()
        focus_spec = self._focus_spec(inputs.get("focus_component"))
        required_trust_phrase = self._required_trust_phrase(inputs)
        seed_material = f"{variant_id}:{goal}:{focus}:{int(time.time() // 45)}"
        rng = Random(seed_material)

        trust_options = self._trust_callout_options(required_trust_phrase)
        cta_options = [
            "Claim Your Offer",
            "Shop The Drop",
            "Unlock This Deal",
        ]
        subheadline_options = [
            "Built for quick visual comparison with premium materials and reliable delivery.",
            "Compare styles faster with premium build quality and smooth delivery.",
            "Made for fast browsing and confident checkout with premium quality.",
        ]
        trust_copy = trust_options[rng.randrange(len(trust_options))]
        cta_copy = cta_options[rng.randrange(len(cta_options))]
        subheadline_copy = subheadline_options[rng.randrange(len(subheadline_options))]

        rank_1 = {
            "rank": 1,
            "change_type": "TRUST_SIGNAL",
            "target_component": "hero.trust_callout",
            "rationale": "Bounce is elevated; stronger trust reduces hesitation.",
            "hypothesis": "Adding warranty and shipping clarity lowers bounce and increases ATC.",
            "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
            "patch": {
                "operations": [
                    {
                                "op": "replace",
                                "path": "hero.trust_callout",
                                "value": trust_copy,
                                "reason": "Improve trust signal clarity",
                            }
                        ]
            },
        }
        rank_2 = {
            "rank": 2,
            "change_type": "CTA",
            "target_component": "hero.cta_text",
            "rationale": "CTA can be more directive for stronger click intent.",
            "hypothesis": "Specific action language raises CTR.",
            "expected_impact_json": {"ctr": "up", "atc": "flat", "bounce": "flat"},
            "patch": {
                "operations": [
                    {
                        "op": "replace",
                        "path": "hero.cta_text",
                        "value": cta_copy,
                        "reason": "Increase action clarity",
                    }
                ]
            },
        }
        rank_3 = {
            "rank": 3,
            "change_type": "LAYOUT",
            "target_component": "product image block",
            "rationale": "Visual emphasis can improve scanning and reduce drop-off before click.",
            "hypothesis": "Reordering hero and image emphasis can improve click quality and engagement.",
            "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
            "patch": {
                "operations": [
                    {
                        "op": "replace",
                        "path": "meta.rationale",
                        "value": "layout:image-first",
                        "reason": "Switch to image-first emphasis for layout experimentation",
                    }
                ]
            },
        }

        if focus_spec and focus_spec["change_type"] == "LAYOUT":
            layout_values = ["layout:text-first", "layout:image-first", "layout:image-stack"]
            payload = {
                "recommendations": [
                    {
                        "rank": idx + 1,
                        "change_type": "LAYOUT",
                        "target_component": "product image block",
                        "rationale": "Refine image/hero composition for clearer scanning.",
                        "hypothesis": "Layout tuning can increase click quality without copy drift.",
                        "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": "meta.rationale",
                                    "value": value,
                                    "reason": "Run a layout-focused test for selected area",
                                }
                            ]
                        },
                    }
                    for idx, value in enumerate(layout_values)
                ]
            }
            return CodexRecommendationResponse.model_validate(payload)

        if focus_spec and focus_spec["target"] == "bullets":
            bullet_paths = ["bullets.0", "bullets.1", "bullets.2"]
            bullet_values = [
                "Fast setup with lower friction on first click",
                "Trusted quality with transparent shipping and returns",
                "Built for confident checkout on mobile",
            ]
            payload = {
                "recommendations": [
                    {
                        "rank": idx + 1,
                        "change_type": "COPY",
                        "target_component": "bullets",
                        "rationale": "Tighten benefit messaging in the bullet grid.",
                        "hypothesis": "Sharper benefit bullets can improve add-to-cart progression.",
                        "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": bullet_paths[idx],
                                    "value": bullet_values[idx],
                                    "reason": "Improve selected bullet block clarity",
                                }
                            ]
                        },
                    }
                    for idx in range(3)
                ]
            }
            return CodexRecommendationResponse.model_validate(payload)

        if focus_spec and focus_spec["path"] in {"banner.text", "banner.badge"}:
            banner_values = [
                "Launch week: save 15% on top accessories",
                "Limited drop: free shipping + 15% launch offer",
                "This week only: premium picks at launch pricing",
            ]
            payload = {
                "recommendations": [
                    {
                        "rank": idx + 1,
                        "change_type": "COPY",
                        "target_component": "banner.text",
                        "rationale": "Strengthen promo clarity in the selected banner area.",
                        "hypothesis": "Cleaner promo framing should raise click-through rate.",
                        "expected_impact_json": {"ctr": "up", "atc": "flat", "bounce": "flat"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": "banner.text",
                                    "value": banner_values[idx],
                                    "reason": "Optimize selected promo banner area",
                                }
                            ]
                        },
                    }
                    for idx in range(3)
                ]
            }
            return CodexRecommendationResponse.model_validate(payload)

        if focus_spec and focus_spec["path"] in {"hero.cta_text", "hero.headline", "hero.subheadline", "hero.trust_callout"}:
            if focus_spec["path"] == "hero.cta_text":
                values = cta_options
                change_type = "CTA"
                rationale = "Refine click-through action copy in the selected CTA."
                hypothesis = "More direct action language should improve click-through rate."
            elif focus_spec["path"] == "hero.trust_callout":
                values = trust_options
                change_type = "TRUST_SIGNAL"
                rationale = "Strengthen trust language in the selected callout."
                hypothesis = "Stronger trust signal should reduce bounce and increase ATC."
            elif focus_spec["path"] == "hero.headline":
                values = [
                    "Everyday Sling built for faster accessory discovery",
                    "Find your next go-to sling in one quick scroll",
                    "Premium sling picks designed for daily carry",
                ]
                change_type = "COPY"
                rationale = "Sharpen headline clarity in the selected hero area."
                hypothesis = "Clearer hero promise should improve first-click intent."
            else:
                values = subheadline_options
                change_type = "COPY"
                rationale = "Clarify value framing in the selected hero text."
                hypothesis = "Sharper subheadline should improve add-to-cart progression."
            payload = {
                "recommendations": [
                    {
                        "rank": idx + 1,
                        "change_type": change_type,
                        "target_component": focus_spec["target"],
                        "rationale": rationale,
                        "hypothesis": hypothesis,
                        "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": focus_spec["path"],
                                    "value": values[idx % len(values)],
                                    "reason": f"Optimize selected area: {focus_spec['target']}",
                                }
                            ]
                        },
                    }
                    for idx in range(3)
                ]
            }
            return CodexRecommendationResponse.model_validate(payload)

        if "layout" in goal or "image" in goal or "layout" in focus or "image" in focus:
            rank_1, rank_2, rank_3 = rank_3, rank_2, rank_1
        elif "cta" in goal or "click" in goal:
            rank_1, rank_2, rank_3 = rank_2, rank_1, rank_3

        if "subheadline" in focus:
            rank_3 = {
                "rank": 3,
                "change_type": "COPY",
                "target_component": "hero.subheadline",
                "rationale": "Selected area can be clearer for faster understanding.",
                "hypothesis": "Sharper benefit framing improves add-to-cart progression.",
                "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                "patch": {
                    "operations": [
                        {
                            "op": "replace",
                            "path": "hero.subheadline",
                            "value": subheadline_copy,
                            "reason": "Improve value clarity on selected area",
                        }
                    ]
                },
            }

        rank_1["rank"] = 1
        rank_2["rank"] = 2
        rank_3["rank"] = 3
        payload = {"recommendations": [rank_1, rank_2, rank_3]}
        parsed = CodexRecommendationResponse.model_validate(payload)
        return self._ensure_recommendation_diversity(inputs, parsed)

    def _recommendation_schema(self) -> dict:
        """Return JSON schema for recommendation responses."""
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "recommendations": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "rank": {"type": "integer"},
                            "change_type": {"type": "string"},
                            "target_component": {"type": "string"},
                            "rationale": {"type": "string"},
                            "hypothesis": {"type": "string"},
                            "expected_impact_json": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "ctr": {"type": ["string", "number", "null"]},
                                    "atc": {"type": ["string", "number", "null"]},
                                    "bounce": {"type": ["string", "number", "null"]},
                                },
                                "required": ["ctr", "atc", "bounce"],
                            },
                            "patch": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "operations": {
                                        "type": "array",
                                        "minItems": 1,
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "op": {"type": "string"},
                                                "path": {"type": "string"},
                                                "value": {"type": ["string", "null"]},
                                                "reason": {"type": "string"},
                                            },
                                            "required": ["op", "path", "value", "reason"],
                                        },
                                    }
                                },
                                "required": ["operations"],
                            },
                        },
                        "required": [
                            "rank",
                            "change_type",
                            "target_component",
                            "rationale",
                            "hypothesis",
                            "expected_impact_json",
                            "patch",
                        ],
                    },
                }
            },
            "required": ["recommendations"],
        }

    def propose_improvements(self, inputs: dict[str, Any]) -> CodexRecommendationResponse:
        """Propose and return improvements."""
        focus_spec = self._focus_spec(inputs.get("focus_component"))
        selected_area_context = inputs.get("selected_area_context")
        has_image = bool(inputs.get("landing_page_snapshot_url"))

        mode_instruction = (
            "Focus mode is active. Generate up to three on-theme alternatives for the selected area only. "
            "Keep brand voice consistent and avoid unrelated component edits."
            if focus_spec
            else "No area is selected. Generate up to three recommendations with diverse change types and avoid trust-only repetition."
        )
        image_instruction = (
            "An attached storefront image is provided. Ground your rationale in visible page structure and component placement."
            if has_image
            else "No image is attached; rely on structured assets and visual_context."
        )
        area_instruction = (
            f"Selected area context: {json.dumps(selected_area_context, ensure_ascii=True)}"
            if isinstance(selected_area_context, dict)
            else "Selected area context is not provided."
        )
        layout_mode_instruction = (
            "For layout-focused output, patch meta.rationale using one of: "
            "layout:text-first, layout:image-first, layout:image-stack."
            if focus_spec and focus_spec.get("path") == "meta.rationale"
            else ""
        )
        system_prompt = (
            "You are an ecommerce optimization sub-agent. Return only strict JSON matching the schema. "
            "Use KPI context, diagnostics, interventions, visual context, and operator goal to produce ranked, concrete patch recommendations. "
            f"{mode_instruction} {image_instruction} {area_instruction} {layout_mode_instruction}"
        )

        try:
            if self.provider != "cli" and not self.api_key:
                raise ValueError("Missing CODEX_API_KEY")
            raw = self._call_openai_json(system_prompt, inputs, "improvement_recommendations", self._recommendation_schema())
            try:
                parsed = CodexRecommendationResponse.model_validate(raw)
            except ValidationError:
                normalized = self._normalize_recommendation_payload(raw)
                parsed = CodexRecommendationResponse.model_validate(normalized)
            if self.provider == "cli":
                logger.info("Codex CLI produced live recommendations for variant_id=%s", inputs.get("variant_id"))
            return self._ensure_recommendation_diversity(inputs, parsed)
        except Exception as exc:
            self._raise_if_live_mode("recommendation", exc)
            logger.warning("Codex live recommendation generation failed; using fallback: %s", exc)
            return self._fallback_recommendations(inputs)

    def validate_patch_json(self, patch_json: dict) -> dict:
        """Validate and normalize a patch payload before apply."""
        return PatchDocument.model_validate(patch_json).model_dump()

    def parse_or_raise(self, raw: str) -> dict:
        """Parse model JSON output and raise on invalid payloads."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid Codex JSON output") from exc

    def validate_assets_or_raise(self, payload: dict) -> dict:
        """Validate assets or raise."""
        try:
            return CampaignAssets.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise ValueError(f"Invalid assets: {exc}") from exc

    def _ensure_recommendation_diversity(
        self, inputs: dict[str, Any], parsed: CodexRecommendationResponse
    ) -> CodexRecommendationResponse:
        """Ensure returned recommendations are diverse and policy-compliant."""
        goal = str(inputs.get("operator_goal") or "").lower()
        focus = str(inputs.get("focus_component") or "").lower()
        focus_spec = self._focus_spec(inputs.get("focus_component"))
        required_trust_phrase = self._required_trust_phrase(inputs)
        selected_area_context = inputs.get("selected_area_context")
        allowed_paths: set[str] = set()
        if isinstance(selected_area_context, dict):
            allowed_paths = {
                str(item)
                for item in selected_area_context.get("allowed_patch_paths", [])
                if isinstance(item, str) and item
            }
        recommendations = list(parsed.recommendations)

        def _matches_focus(rec: CodexImprovementRecommendation, target: str, path: str) -> bool:
            """Execute matches focus."""
            return rec.target_component == target or any(
                op.path == path or (op.path.startswith("bullets.") and target == "bullets")
                for op in rec.patch.operations
            )

        def _allowed_for_focus(rec: CodexImprovementRecommendation) -> bool:
            """Execute allowed for focus."""
            if not allowed_paths:
                return True
            return all(op.path in allowed_paths for op in rec.patch.operations)

        if focus_spec:
            target = focus_spec["target"]
            path = focus_spec["path"]
            focused = [
                rec
                for rec in recommendations
                if _matches_focus(rec, target, path)
            ]
            focused = [rec for rec in focused if _allowed_for_focus(rec)]
            if path == "hero.trust_callout" and required_trust_phrase:
                for rec in focused:
                    for op in rec.patch.operations:
                        if op.path == "hero.trust_callout" and op.value is not None:
                            op.value = self._enforce_trust_phrase(str(op.value), required_trust_phrase)
            if len(focused) < 3:
                fallback = self._fallback_recommendations(inputs)
                seen = {
                    json.dumps(rec.patch.model_dump(), sort_keys=True, ensure_ascii=True)
                    for rec in focused
                }
                for rec in fallback.recommendations:
                    if not _matches_focus(rec, target, path):
                        continue
                    if not _allowed_for_focus(rec):
                        continue
                    sig = json.dumps(rec.patch.model_dump(), sort_keys=True, ensure_ascii=True)
                    if sig in seen:
                        continue
                    focused.append(rec)
                    seen.add(sig)
                    if len(focused) >= 3:
                        break
            if focused:
                for idx, rec in enumerate(focused[:3], start=1):
                    rec.rank = idx
                return CodexRecommendationResponse(recommendations=focused[:3])
            if target == "bullets":
                bullet_paths = ["bullets.0", "bullets.1", "bullets.2"]
                values = [
                    "Fast setup with lower friction on first click",
                    "Trusted quality with transparent shipping and returns",
                    "Built for confident checkout on mobile",
                ]
            elif path == "banner.text":
                bullet_paths = ["banner.text", "banner.text", "banner.text"]
                values = [
                    "Launch week: save 15% on top accessories",
                    "Limited drop: free shipping + 15% launch offer",
                    "This week only: premium picks at launch pricing",
                ]
            elif path == "hero.cta_text":
                bullet_paths = [path, path, path]
                values = ["Claim Your Offer", "Shop The Drop", "Unlock This Deal"]
            elif path == "hero.trust_callout":
                bullet_paths = [path, path, path]
                values = self._trust_callout_options(required_trust_phrase)
            elif path == "meta.rationale":
                bullet_paths = [path, path, path]
                values = ["layout:text-first", "layout:image-first", "layout:image-stack"]
            else:
                bullet_paths = [path, path, path]
                values = [
                    "Sharper message for this selected section.",
                    "Clearer value framing for this selected section.",
                    "Higher-intent wording for this selected section.",
                ]
            fallback_focused = [
                CodexImprovementRecommendation.model_validate(
                    {
                        "rank": idx + 1,
                        "change_type": focus_spec["change_type"],
                        "target_component": target,
                        "rationale": "Prioritizing your selected storefront area.",
                        "hypothesis": "Focused edits on the selected area should improve KPI efficiency.",
                        "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": bullet_paths[idx],
                                    "value": values[idx],
                                    "reason": f"Focus optimization for {target}",
                                }
                            ]
                        },
                    }
                )
                for idx in range(3)
            ]
            return CodexRecommendationResponse(recommendations=fallback_focused)

        used_change_types = {rec.change_type.value for rec in recommendations}

        templates: list[dict[str, Any]] = []
        if "layout" in goal or "image" in goal or "layout" in focus or "image" in focus:
            templates.append(
                {
                    "change_type": "LAYOUT",
                    "target_component": "product image block",
                    "rationale": "Requested layout focus: emphasize visual hierarchy first.",
                    "hypothesis": "Image-first arrangement can lift scan quality and clicks.",
                    "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                    "patch": {
                        "operations": [
                            {
                                "op": "replace",
                                "path": "meta.rationale",
                                "value": "layout:image-first",
                                "reason": "Apply layout-first visual hierarchy",
                            }
                        ]
                    },
                }
            )
        templates.extend(
            [
                {
                    "change_type": "CTA",
                    "target_component": "hero.cta_text",
                    "rationale": "Specific action language can raise click intent.",
                    "hypothesis": "A sharper click-through action should increase click-through rate.",
                    "expected_impact_json": {"ctr": "up", "atc": "flat", "bounce": "flat"},
                    "patch": {
                        "operations": [
                            {
                                "op": "replace",
                                "path": "hero.cta_text",
                                "value": "Claim Your Offer",
                                "reason": "Improve action clarity",
                            }
                        ]
                    },
                },
                {
                    "change_type": "COPY",
                    "target_component": "hero.subheadline",
                    "rationale": "Clarifying value proposition helps post-click quality.",
                    "hypothesis": "Sharper benefit language should improve add-to-cart progression.",
                    "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                    "patch": {
                        "operations": [
                            {
                                "op": "replace",
                                "path": "hero.subheadline",
                                "value": "Built for quick visual comparison with premium materials and reliable delivery.",
                                "reason": "Improve value clarity",
                            }
                        ]
                    },
                },
                {
                    "change_type": "TRUST_SIGNAL",
                    "target_component": "hero.trust_callout",
                    "rationale": "Trust language reduces hesitation before checkout.",
                    "hypothesis": "Guarantee clarity should reduce bounce and increase ATC.",
                    "expected_impact_json": {"ctr": "up", "atc": "up", "bounce": "down"},
                    "patch": {
                        "operations": [
                            {
                                "op": "replace",
                                "path": "hero.trust_callout",
                                "value": "Free shipping, 1-year warranty, and hassle-free returns",
                                "reason": "Strengthen trust callout",
                            }
                        ]
                    },
                },
            ]
        )

        for template in templates:
            if len(recommendations) >= 3:
                break
            if template["change_type"] in used_change_types:
                continue
            recommendations.append(
                CodexImprovementRecommendation.model_validate(
                    {
                        "rank": len(recommendations) + 1,
                        **template,
                    }
                )
            )
            used_change_types.add(template["change_type"])

        # Keep max three and normalize rank order with unique change types where possible.
        recommendations = recommendations[:3]
        normalized: list[CodexImprovementRecommendation] = []
        seen: set[str] = set()
        for rec in recommendations:
            if rec.change_type.value in seen:
                replacement_template = next((t for t in templates if t["change_type"] not in seen), None)
                if replacement_template:
                    rec = CodexImprovementRecommendation.model_validate(
                        {
                            "rank": rec.rank,
                            **replacement_template,
                        }
                    )
            if rec.change_type.value in seen:
                continue
            seen.add(rec.change_type.value)
            normalized.append(rec)

        while len(normalized) < 3:
            filler = next((t for t in templates if t["change_type"] not in {n.change_type.value for n in normalized}), None)
            if not filler:
                break
            normalized.append(
                CodexImprovementRecommendation.model_validate(
                    {
                        "rank": len(normalized) + 1,
                        **filler,
                    }
                )
            )

        for idx, rec in enumerate(normalized[:3], start=1):
            rec.rank = idx
        return CodexRecommendationResponse(recommendations=normalized[:3])

    @staticmethod
    def _required_trust_phrase(inputs: dict[str, Any]) -> str:
        """Extract the required trust phrase from campaign constraints when present."""
        campaign = inputs.get("campaign")
        if not isinstance(campaign, dict):
            return ""
        constraints = campaign.get("constraints")
        if not isinstance(constraints, dict):
            return ""
        phrase = constraints.get("required_trust_phrase")
        return str(phrase or "").strip().lower()

    @classmethod
    def _enforce_trust_phrase(cls, value: str, required_phrase: str) -> str:
        """Ensure trust-copy value contains the required trust phrase."""
        phrase = (required_phrase or "").strip().lower()
        if not phrase:
            return value
        current = value.strip()
        if phrase in current.lower():
            return current
        suffix = required_phrase.strip()
        if not suffix:
            return current
        connector = "; " if current else ""
        return f"{current}{connector}{suffix.title()} included"

    @classmethod
    def _trust_callout_options(cls, required_phrase: str) -> list[str]:
        """Return three trust-callout variants that satisfy required trust phrasing."""
        base = [
            "Free shipping, 1-year warranty, and free returns",
            "1-year warranty, secure checkout, and free returns on every order",
            "Fast delivery, free returns, and a 1-year warranty included",
        ]
        return [cls._enforce_trust_phrase(item, required_phrase) for item in base]

    @staticmethod
    def _normalize_patch_path(path: str) -> str:
        """Normalize patch paths to supported asset schema paths."""
        cleaned = (path or "").strip()
        if cleaned.startswith("/assets/"):
            cleaned = cleaned[len("/assets/") :]
        elif cleaned.startswith("/"):
            cleaned = cleaned[1:]
        cleaned = cleaned.replace("/", ".")
        cleaned = cleaned.replace(".ctaText", ".cta_text")
        cleaned = cleaned.replace(".trustCallout", ".trust_callout")
        cleaned = cleaned.replace(".strategyTag", ".strategy_tag")
        return cleaned

    def _normalize_recommendation_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize and sanitize recommendation payload structure."""
        recommendations = raw.get("recommendations", []) if isinstance(raw, dict) else []
        normalized: list[dict[str, Any]] = []
        change_type_aliases = {
            "BANNER": "COPY",
            "HEADLINE": "COPY",
            "SUBHEADLINE": "COPY",
            "TRUST": "TRUST_SIGNAL",
        }
        default_paths_by_type = {
            "TRUST_SIGNAL": "hero.trust_callout",
            "CTA": "hero.cta_text",
            "LAYOUT": "meta.rationale",
            "CONFIG": "meta.rationale",
            "CODE": "meta.rationale",
            "COPY": "hero.subheadline",
        }

        for idx, rec in enumerate(recommendations[:3], start=1):
            if not isinstance(rec, dict):
                continue
            change_type = str(rec.get("change_type", "COPY")).upper()
            change_type = change_type_aliases.get(change_type, change_type)
            if change_type not in {"COPY", "LAYOUT", "TRUST_SIGNAL", "CTA", "CONFIG", "CODE"}:
                change_type = "COPY"

            patch = rec.get("patch", {})
            operations = patch.get("operations", []) if isinstance(patch, dict) else []
            fixed_ops: list[dict[str, Any]] = []
            for op in operations:
                if not isinstance(op, dict):
                    continue
                normalized_path = self._normalize_patch_path(str(op.get("path", "")))
                if normalized_path not in ALLOWED_PATHS:
                    normalized_path = default_paths_by_type.get(change_type, "hero.subheadline")
                fixed_ops.append(
                    {
                        "op": "replace",
                        "path": normalized_path,
                        "value": op.get("value"),
                        "reason": str(op.get("reason") or "Apply recommended optimization"),
                    }
                )
            if not fixed_ops:
                fallback_path = default_paths_by_type.get(change_type, "hero.subheadline")
                fallback_value = rec.get("target_component") or rec.get("rationale") or "Updated campaign copy"
                fixed_ops = [
                    {
                        "op": "replace",
                        "path": fallback_path,
                        "value": fallback_value,
                        "reason": "Apply recommended optimization",
                    }
                ]

            expected = rec.get("expected_impact_json")
            if not isinstance(expected, dict):
                expected = {}
            expected = {
                "ctr": expected.get("ctr", "up"),
                "atc": expected.get("atc", "up"),
                "bounce": expected.get("bounce", "down"),
            }

            normalized.append(
                {
                    "rank": idx,
                    "change_type": change_type,
                    "target_component": str(rec.get("target_component") or "Storefront copy"),
                    "rationale": str(rec.get("rationale") or "Expected to improve campaign KPI balance."),
                    "hypothesis": str(rec.get("hypothesis") or "Targeted copy/layout adjustments should improve outcomes."),
                    "expected_impact_json": expected,
                    "patch": {"operations": fixed_ops},
                }
            )
        return {"recommendations": normalized}

    def _fallback_variant_advice(self, inputs: dict[str, Any]) -> VariantAdviceResponse:
        """Return deterministic best-variant advice from KPI inputs."""
        objective = inputs.get("objective", "CTR")
        variants = inputs.get("variants", [])
        if not variants:
            return VariantAdviceResponse(
                best_variant_id=0,
                best_variant_name=None,
                confidence=0.0,
                rationale="No variants available.",
                next_step="Generate variants first.",
            )

        def score(item: dict) -> float:
            """Execute score."""
            ctr = item.get("ctr") or 0
            atc = item.get("atc_rate") or 0
            bounce = item.get("bounce_rate") or 0
            if objective == "ATC":
                return atc * 100 - bounce * 10 + ctr * 20
            if objective == "CONVERSION":
                return atc * 80 + ctr * 20 - bounce * 20
            return ctr * 100 + atc * 20 - bounce * 15

        ranked = sorted(variants, key=score, reverse=True)
        best = ranked[0]
        return VariantAdviceResponse(
            best_variant_id=int(best["variant_id"]),
            best_variant_name=str(best.get("variant_name") or f"Variant {best['variant_id']}"),
            confidence=0.72,
            rationale="This variant currently shows the strongest KPI blend for the selected optimization goal.",
            next_step="Run one more simulation batch, then apply the top low-risk recommendation for this variant.",
        )

    def _variant_advice_schema(self) -> dict:
        """Return JSON schema for best-variant advice responses."""
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "best_variant_id": {"type": "integer"},
                "best_variant_name": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
                "next_step": {"type": "string"},
            },
            "required": ["best_variant_id", "best_variant_name", "confidence", "rationale", "next_step"],
        }

    def advise_best_variant(self, inputs: dict[str, Any]) -> VariantAdviceResponse:
        """Select the best variant from KPI signals and user goal."""
        system_prompt = (
            "You are a commerce experimentation analyst. Pick the best variant for the stated goal using KPI signals. "
            "Return only strict JSON matching the schema."
        )
        try:
            if self.provider != "cli" and not self.api_key:
                raise ValueError("Missing CODEX_API_KEY")
            raw = self._call_openai_json(system_prompt, inputs, "variant_advice", self._variant_advice_schema())
            return VariantAdviceResponse.model_validate(raw)
        except Exception as exc:
            self._raise_if_live_mode("variant advice", exc)
            logger.warning("Codex live variant advice failed; using fallback: %s", exc)
            return self._fallback_variant_advice(inputs)
    @staticmethod
    def _focus_spec(focus_component: str | None) -> dict[str, Any] | None:
        """Execute focus spec."""
        focus = (focus_component or "").strip().lower()
        if not focus:
            return None
        if focus == "hero.headline":
            return {"path": "hero.headline", "target": "hero.headline", "change_type": "COPY"}
        if focus == "hero.subheadline":
            return {"path": "hero.subheadline", "target": "hero.subheadline", "change_type": "COPY"}
        if focus == "hero.cta_text":
            return {"path": "hero.cta_text", "target": "hero.cta_text", "change_type": "CTA"}
        if focus == "hero.trust_callout":
            return {"path": "hero.trust_callout", "target": "hero.trust_callout", "change_type": "TRUST_SIGNAL"}
        if focus == "banner.text":
            return {"path": "banner.text", "target": "banner.text", "change_type": "COPY"}
        if focus == "banner.badge":
            return {"path": "banner.badge", "target": "banner.badge", "change_type": "COPY"}
        if focus == "bullets":
            return {"path": "bullets.0", "target": "bullets", "change_type": "COPY"}
        if focus.startswith("bullets."):
            return {"path": focus if focus in ALLOWED_PATHS else "bullets.0", "target": "bullets", "change_type": "COPY"}
        if "image" in focus or "layout" in focus:
            return {"path": "meta.rationale", "target": "product image block", "change_type": "LAYOUT"}
        return {"path": "hero.subheadline", "target": focus_component, "change_type": "COPY"}
