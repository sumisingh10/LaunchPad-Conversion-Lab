"""API route module for   init   endpoints.
Defines route handlers and request/response contracts for this API area.
"""
from app.api import auth, campaigns, lift_trace, metrics, recommendations, system, variants

__all__ = ["auth", "campaigns", "variants", "metrics", "recommendations", "lift_trace", "system"]
