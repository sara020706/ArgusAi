"""Event scoring routes for the Argus API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus import ArgusEngine, Event, build_explanation
from argus.api.dependencies import get_engine

router = APIRouter(prefix="/v1/events", tags=["events"])

# Maximum events accepted in a single batch request.
MAX_BATCH_SIZE = 100


class EventRequest(BaseModel):
    """Incoming event payload for scoring."""

    user_id: str
    timestamp: datetime
    ip: str
    device_id: str
    download_mb: float = 0.0
    files_accessed: int = 0
    action: str = "login"
    location: str | None = None


class ScoreResponse(BaseModel):
    """Scoring result returned to API clients."""

    user_id: str
    timestamp: datetime
    risk_score: float
    risk_level: str
    reasons: list[str]
    rule_contributions: dict
    stat_contributions: dict
    explanation: str


def _to_event(req: EventRequest) -> Event:
    """Convert an :class:`EventRequest` into a domain :class:`Event`.

    Args:
        req: The validated request model.

    Returns:
        The corresponding :class:`~argus.schema.Event`.
    """
    return Event(
        user_id=req.user_id,
        timestamp=req.timestamp,
        ip=req.ip,
        device_id=req.device_id,
        download_mb=req.download_mb,
        files_accessed=req.files_accessed,
        action=req.action,
        location=req.location,
    )


def _to_response(engine: ArgusEngine, event: Event) -> ScoreResponse:
    """Score an event and build its :class:`ScoreResponse`.

    Args:
        engine: The shared scoring engine.
        event: The event to score.

    Returns:
        A fully populated :class:`ScoreResponse`.
    """
    result = engine.score(event)
    return ScoreResponse(
        user_id=result.user_id,
        timestamp=result.timestamp,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        reasons=result.reasons,
        rule_contributions=result.rule_contributions,
        stat_contributions=result.stat_contributions,
        explanation=build_explanation(result),
    )


@router.post("/score", response_model=ScoreResponse)
def score_event(
    req: EventRequest, engine: ArgusEngine = Depends(get_engine)
) -> ScoreResponse:
    """Score a single user activity event.

    Returns the risk score, risk level, contributing factors, and a full
    human-readable explanation.
    """
    return _to_response(engine, _to_event(req))


@router.post("/batch", response_model=list[ScoreResponse])
def score_batch(
    reqs: list[EventRequest], engine: ArgusEngine = Depends(get_engine)
) -> list[ScoreResponse]:
    """Score multiple events in one request.

    Accepts up to 100 events and returns a list of score responses. Requests
    exceeding the limit are rejected with HTTP 422.
    """
    if len(reqs) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"Batch size {len(reqs)} exceeds maximum of {MAX_BATCH_SIZE}",
        )
    return [_to_response(engine, _to_event(req)) for req in reqs]
