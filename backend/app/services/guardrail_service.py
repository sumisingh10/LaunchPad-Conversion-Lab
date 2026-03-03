"""Service-layer module for guardrail service.
Implements business rules and orchestration for this domain area.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas.patch import PatchDocument


@dataclass
class GuardrailResult:
    """Service component for guardrail result."""
    allowed: bool
    risk_level: str
    violations: list[str]
    operations_count: int


class GuardrailService:
    """Service layer for guardrail workflows."""
    def _get_path_value(self, assets: dict, path: str):
        """Execute get path value."""
        cursor = assets
        for part in path.split("."):
            if isinstance(cursor, list):
                cursor = cursor[int(part)]
            else:
                cursor = cursor.get(part)
        return cursor

    def assess_patch(self, assets: dict, patch_doc: PatchDocument, constraints: dict | None = None) -> GuardrailResult:
        """Evaluate patch operations against campaign guardrail policies."""
        constraints = constraints or {}
        max_operations = int(constraints.get("max_patch_operations", 2))
        max_char_delta = int(constraints.get("max_char_delta_per_change", 80))
        banned_terms = [str(t).lower() for t in constraints.get("banned_terms", [])]

        violations: list[str] = []

        if len(patch_doc.operations) > max_operations:
            violations.append(f"Too many operations ({len(patch_doc.operations)} > {max_operations})")

        for op in patch_doc.operations:
            previous = self._get_path_value(assets, op.path)
            previous_str = "" if previous is None else str(previous)
            next_str = "" if op.value is None else str(op.value)

            delta = abs(len(next_str) - len(previous_str))
            if delta > max_char_delta:
                violations.append(f"Change too large on {op.path} ({delta} chars delta)")

            lowered_value = next_str.lower()
            for term in banned_terms:
                if term and term in lowered_value:
                    violations.append(f"Banned term used in {op.path}: {term}")

        required_trust_phrase = str(constraints.get("required_trust_phrase", "")).lower().strip()
        if required_trust_phrase:
            trust_value = assets.get("hero", {}).get("trust_callout", "")
            replacement = None
            for op in patch_doc.operations:
                if op.path == "hero.trust_callout":
                    replacement = "" if op.value is None else str(op.value)
            final_trust = replacement if replacement is not None else trust_value
            if required_trust_phrase not in final_trust.lower():
                violations.append(f"Required trust phrase missing: {required_trust_phrase}")

        if violations:
            risk_level = "HIGH" if len(violations) >= 2 else "MEDIUM"
            return GuardrailResult(False, risk_level, violations, len(patch_doc.operations))

        risk_level = "LOW" if len(patch_doc.operations) == 1 else "MEDIUM"
        return GuardrailResult(True, risk_level, [], len(patch_doc.operations))

    def recommendation_score(self, rank: int, risk_level: str, has_metrics: bool) -> int:
        """Score a recommendation based on risk and metric context."""
        score = 100
        score -= max(rank - 1, 0) * 12
        score -= {"LOW": 0, "MEDIUM": 15, "HIGH": 30}.get(risk_level, 10)
        if not has_metrics:
            score -= 10
        return max(0, min(100, score))
