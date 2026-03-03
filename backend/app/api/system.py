"""API route module for system endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.services.codex_service import CodexService

router = APIRouter(tags=["system"])


@router.get("/system/codex-auth-status")
def codex_auth_status(current_user: User = Depends(get_current_user)):
    """Execute codex auth status."""
    _ = current_user
    provider = (settings.codex_provider or "cli").lower()
    cli_path = settings.codex_cli_path or "codex"
    cli_available = bool(shutil.which(cli_path) if "/" not in cli_path else Path(cli_path).exists())
    cli_auth_file = Path("/root/.codex/auth.json")
    has_cli_session = cli_auth_file.exists()
    has_api_key = bool(CodexService._load_api_key())

    connected = (provider == "cli" and cli_available and has_cli_session) or (provider == "api" and has_api_key)

    return {
        "provider": provider,
        "connected": connected,
        "fallback_enabled": settings.codex_use_fallback,
        "cli_available": cli_available,
        "has_cli_session": has_cli_session if provider == "cli" else None,
        "has_api_key": has_api_key if provider == "api" else None,
    }

