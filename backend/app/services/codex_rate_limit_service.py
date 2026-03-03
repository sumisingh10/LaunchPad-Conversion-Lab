"""Service-layer module for codex rate limit service.
Implements business rules and orchestration for this domain area.
"""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import threading

from fastapi import HTTPException

from app.core.config import settings


class CodexRateLimitService:
    """Service layer for codex rate limit workflows."""
    _lock = threading.Lock()
    _events: dict[str, deque[datetime]] = defaultdict(deque)

    def _bucket(self, user_id: int, operation: str) -> str:
        """Return the in-memory timestamp bucket for a user-action key."""
        return f"{operation}:{user_id}"

    def check(self, user_id: int, operation: str) -> None:
        """Enforce Codex request rate limits per user and action."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        key = self._bucket(user_id, operation)

        with self._lock:
            q = self._events[key]
            while q and q[0] < window_start:
                q.popleft()

            if len(q) >= settings.codex_requests_per_minute:
                retry_after = max(1, int((q[0] + timedelta(minutes=1) - now).total_seconds()))
                raise HTTPException(
                    status_code=429,
                    detail=f"Codex rate limit exceeded for {operation}. Retry in {retry_after}s.",
                )

            q.append(now)
