"""Per-user profile, event, and risk-summary routes for the Argus API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from argus import ArgusEngine, UserProfile
from argus.api.dependencies import get_engine

router = APIRouter(prefix="/v1/users", tags=["users"])


class UserProfileResponse(BaseModel):
    """Behavioral profile response for a user."""

    user_id: str
    avg_download_mb: float
    std_download_mb: float
    avg_files_accessed: float
    known_ips: list[str]
    known_devices: list[str]
    event_count: int
    last_seen: str | None
    profile_mature: bool


class RiskSummary(BaseModel):
    """Concise risk summary response for a user."""

    user_id: str
    recent_high_alerts: int
    last_risk_score: float | None
    last_risk_level: str | None
    risk_trend: str


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_profile(
    user_id: str, engine: ArgusEngine = Depends(get_engine)
) -> UserProfileResponse:
    """Return the behavioral profile for a user.

    Responds with 404 if the user has no profile yet.
    """
    stored = engine.store.get_profile(user_id)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"User {user_id!r} not found")

    profile = UserProfile.from_dict(stored)
    return UserProfileResponse(
        user_id=profile.user_id,
        avg_download_mb=profile.avg_download_mb,
        std_download_mb=profile.std_download_mb,
        avg_files_accessed=profile.avg_files_accessed,
        known_ips=sorted(profile.known_ips),
        known_devices=sorted(profile.known_devices),
        event_count=profile.event_count,
        last_seen=profile.last_seen.isoformat() if profile.last_seen else None,
        profile_mature=profile.is_mature(),
    )


@router.get("/{user_id}/events", response_model=list[dict])
def get_events(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    engine: ArgusEngine = Depends(get_engine),
) -> list[dict]:
    """Return recent events for a user, newest first.

    Query param:
        limit: Maximum number of events to return (default 50).
    """
    return engine.get_user_events(user_id, limit=limit)


@router.get("/{user_id}/risk_summary", response_model=RiskSummary)
def risk_summary(
    user_id: str, engine: ArgusEngine = Depends(get_engine)
) -> RiskSummary:
    """Return a risk summary for a user.

    Includes the count of recent high/critical alerts, the most recent risk
    score and level, and a coarse trend ("increasing", "stable", or
    "decreasing") derived from the last few scores.
    """
    events = engine.get_user_events(user_id, limit=50)
    if not events:
        raise HTTPException(status_code=404, detail=f"User {user_id!r} not found")

    # Events come back newest-first.
    recent_high = sum(
        1 for e in events if e.get("risk_level") in ("HIGH", "CRITICAL")
    )
    last_event = events[0]
    last_score = last_event.get("risk_score")
    last_level = last_event.get("risk_level")

    risk_trend = _compute_trend([e.get("risk_score", 0.0) for e in events])

    return RiskSummary(
        user_id=user_id,
        recent_high_alerts=recent_high,
        last_risk_score=last_score,
        last_risk_level=last_level,
        risk_trend=risk_trend,
    )


def _compute_trend(scores_newest_first: list[float], delta: float = 5.0) -> str:
    """Derive a coarse risk trend from recent scores.

    Compares the mean of the most recent few scores against the mean of the
    preceding few.

    Args:
        scores_newest_first: Risk scores ordered newest-first.
        delta: Minimum mean difference to call a trend non-stable.

    Returns:
        ``"increasing"``, ``"decreasing"`` or ``"stable"``.
    """
    if len(scores_newest_first) < 2:
        return "stable"

    window = min(3, len(scores_newest_first) // 2) or 1
    recent = scores_newest_first[:window]
    prior = scores_newest_first[window : window * 2] or scores_newest_first[window:]
    if not prior:
        return "stable"

    recent_avg = sum(recent) / len(recent)
    prior_avg = sum(prior) / len(prior)

    if recent_avg - prior_avg > delta:
        return "increasing"
    if prior_avg - recent_avg > delta:
        return "decreasing"
    return "stable"
