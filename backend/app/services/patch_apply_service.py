"""Service-layer module for patch apply service.
Implements business rules and orchestration for this domain area.
"""
from copy import deepcopy

from pydantic import ValidationError

from app.schemas.assets import CampaignAssets
from app.schemas.patch import PatchDocument


class PatchApplyService:
    """Service layer for patch apply workflows."""
    def apply_patch(self, assets: dict, patch_doc: PatchDocument) -> dict:
        """Apply and persist patch."""
        updated = deepcopy(assets)
        for op in patch_doc.operations:
            path = op.path.split(".")
            cursor = updated
            for i, part in enumerate(path):
                is_last = i == len(path) - 1
                if part.isdigit():
                    idx = int(part)
                    if is_last:
                        cursor[idx] = op.value
                    else:
                        cursor = cursor[idx]
                else:
                    if is_last:
                        cursor[part] = op.value
                    else:
                        cursor = cursor[part]

        try:
            validated = CampaignAssets.model_validate(updated)
        except ValidationError as exc:
            raise ValueError(f"Patched assets failed validation: {exc}") from exc
        return validated.model_dump()
