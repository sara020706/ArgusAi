"""Health and metrics routes for the Argus API.

The ``/health`` endpoint is intentionally robust: it always returns HTTP 200
(even when the engine is degraded or uninitialized) and never raises, so it is
safe to use as a liveness/readiness probe.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import argus
from argus.api import dependencies

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    version: str
    engine_initialized: bool
    ml_enabled: bool
    threat_intel_enabled: bool
    db_connected: bool
    uptime_seconds: float


class MetricsResponse(BaseModel):
    """System metrics response."""

    total_events_scored: int
    total_users_tracked: int
    alerts_generated: int
    avg_score_last_100: float
    engine_uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check. Always returns 200, even when degraded.

    Reports whether the engine is initialized, which optional layers are
    enabled, and whether the database responds. All internal errors are caught
    so this endpoint never returns 500.
    """
    engine = dependencies._engine
    engine_initialized = engine is not None
    ml_enabled = False
    threat_intel_enabled = False
    db_connected = False

    if engine is not None:
        try:
            ml_enabled = engine.detector is not None and engine.detector.is_trained
        except Exception:
            ml_enabled = False
        threat_intel_enabled = engine.threat_intel is not None
        try:
            # A lightweight stats call confirms the store is reachable.
            engine.get_stats()
            db_connected = True
        except Exception:
            db_connected = False

    status = "healthy" if (engine_initialized and db_connected) else "degraded"

    return HealthResponse(
        status=status,
        version=getattr(argus, "__version__", "unknown"),
        engine_initialized=engine_initialized,
        ml_enabled=ml_enabled,
        threat_intel_enabled=threat_intel_enabled,
        db_connected=db_connected,
        uptime_seconds=dependencies.get_uptime_seconds(),
    )


@router.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    """Return system metrics for monitoring."""
    engine = dependencies._engine

    total_events = 0
    total_users = 0
    alerts = 0
    avg_last_100 = 0.0

    if engine is not None:
        try:
            stats = engine.get_stats()
            total_events = stats.get("total_events", 0)
            total_users = stats.get("total_users", 0)
        except Exception:
            pass
        try:
            recent = engine.get_recent_alerts(limit=200, min_risk_level="MEDIUM")
            alerts = len(recent)
            last_100 = engine.get_recent_alerts(limit=100, min_risk_level="LOW")
            scores = [a.get("risk_score", 0.0) for a in last_100]
            if scores:
                avg_last_100 = sum(scores) / len(scores)
        except Exception:
            pass

    return MetricsResponse(
        total_events_scored=total_events,
        total_users_tracked=total_users,
        alerts_generated=alerts,
        avg_score_last_100=avg_last_100,
        engine_uptime_seconds=dependencies.get_uptime_seconds(),
    )
