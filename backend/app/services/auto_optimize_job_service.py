"""Background job service for non-blocking auto-optimization requests.
Runs Codex optimization work in a daemon thread and exposes pollable job status.
"""
from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.db import SessionLocal
from app.models.user import User
from app.services.recommendation_service import RecommendationService


class AutoOptimizeJobService:
    """Manage in-memory async jobs for compare-page auto optimization."""

    _lock = Lock()
    _jobs: dict[str, dict] = {}

    @classmethod
    def start_job(
        cls,
        campaign_id: int,
        user_id: int,
        user_goal: str,
        preferred_variant_id: int | None = None,
    ) -> dict:
        """Create and enqueue an auto-optimize job for background execution."""
        job_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "job_id": job_id,
            "campaign_id": campaign_id,
            "user_id": user_id,
            "status": "QUEUED",
            "created_at": created_at,
            "updated_at": created_at,
            "result": None,
            "error": None,
        }
        with cls._lock:
            cls._jobs[job_id] = payload

        worker = Thread(
            target=cls._run_job,
            kwargs={
                "job_id": job_id,
                "campaign_id": campaign_id,
                "user_id": user_id,
                "user_goal": user_goal,
                "preferred_variant_id": preferred_variant_id,
            },
            daemon=True,
        )
        worker.start()
        return payload.copy()

    @classmethod
    def get_job(cls, campaign_id: int, user_id: int, job_id: str) -> dict:
        """Return a single job status payload scoped to campaign and user."""
        with cls._lock:
            payload = cls._jobs.get(job_id)
            if not payload:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Optimization job not found")
            if payload["campaign_id"] != campaign_id or payload["user_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Optimization job not found")
            return payload.copy()

    @classmethod
    def _update_job(cls, job_id: str, **changes) -> None:
        """Apply an atomic status update to a tracked job record."""
        with cls._lock:
            payload = cls._jobs.get(job_id)
            if not payload:
                return
            payload.update(changes)
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    @classmethod
    def _run_job(
        cls,
        job_id: str,
        campaign_id: int,
        user_id: int,
        user_goal: str,
        preferred_variant_id: int | None,
    ) -> None:
        """Execute a queued auto-optimize job in a dedicated DB session."""
        cls._update_job(job_id, status="RUNNING")
        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                raise ValueError("User not found for optimization job")

            result = RecommendationService(db).auto_optimize(
                campaign_id=campaign_id,
                user=user,
                user_goal=user_goal,
                preferred_variant_id=preferred_variant_id,
            )
            cls._update_job(job_id, status="SUCCEEDED", result=result, error=None)
        except Exception as exc:  # pragma: no cover - exact failure types vary by provider/runtime.
            cls._update_job(job_id, status="FAILED", result=None, error=str(exc))
        finally:
            db.close()
