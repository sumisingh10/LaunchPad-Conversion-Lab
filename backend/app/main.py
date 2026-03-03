"""Module for main in LaunchPad Conversion Lab.
Contains runtime logic for this repository area.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, campaigns, lift_trace, metrics, recommendations, system, variants
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
app = FastAPI(title=settings.app_name)
allowed_origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(variants.router)
app.include_router(metrics.router)
app.include_router(recommendations.router)
app.include_router(lift_trace.router)
app.include_router(system.router)


@app.get("/health")
def healthcheck():
    """Return service health status check."""
    return {"status": "ok"}
