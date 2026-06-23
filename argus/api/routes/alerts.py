"""Alert listing and statistics routes for the Argus API."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from argus import ArgusEngine
from argus.api.dependencies import get_engine

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])

_VALID_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
# Maximum alerts returnable in one request.
MAX_LIMIT = 200


class AlertStats(BaseModel):
    """Aggregate alert statistics response."""

    total_events_today: int
    alerts_today: int
    critical_count: int
    high_count: int
    medium_count: int
    most_active_users: list[str]


@router.get("", response_model=list[dict])
def list_alerts(
    limit: int = Query(50, ge=1, le=MAX_LIMIT),
    min_risk_level: str = Query("MEDIUM"),
    engine: ArgusEngine = Depends(get_engine),
) -> list[dict]:
    """Return recent alerts at or above a minimum risk level.

    Query params:
        limit: Maximum number of alerts (1-200, default 50).
        min_risk_level: One of LOW, MEDIUM, HIGH, CRITICAL (default MEDIUM).
    """
    level = min_risk_level.upper()
    if level not in _VALID_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid min_risk_level: {min_risk_level!r}",
        )
    return engine.get_recent_alerts(limit=limit, min_risk_level=level)


@router.get("/stats", response_model=AlertStats)
def alert_stats(engine: ArgusEngine = Depends(get_engine)) -> AlertStats:
    """Return alert statistics.

    Includes today's event and alert counts, a breakdown of alert levels, and
    the five most active users by alert count.
    """
    # Pull a generous slice of recent alerts to aggregate from.
    alerts = engine.get_recent_alerts(limit=MAX_LIMIT, min_risk_level="LOW")
    today = datetime.now(timezone.utc).date().isoformat()

    today_alerts = [a for a in alerts if str(a.get("timestamp", ""))[:10] == today]
    level_counts = Counter(a.get("risk_level") for a in alerts)

    medium_plus_today = sum(
        1
        for a in today_alerts
        if a.get("risk_level") in ("MEDIUM", "HIGH", "CRITICAL")
    )

    user_counter = Counter(
        a.get("user_id")
        for a in alerts
        if a.get("risk_level") in ("MEDIUM", "HIGH", "CRITICAL")
    )
    most_active = [user for user, _ in user_counter.most_common(5)]

    return AlertStats(
        total_events_today=len(today_alerts),
        alerts_today=medium_plus_today,
        critical_count=level_counts.get("CRITICAL", 0),
        high_count=level_counts.get("HIGH", 0),
        medium_count=level_counts.get("MEDIUM", 0),
        most_active_users=most_active,
    )
