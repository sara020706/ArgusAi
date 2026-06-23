"""Behavioral DNA routes for the Argus API — Phase 9.

Exposes per-user behavioral fingerprints, a cross-user summary sorted by
self-similarity (most drifted first), and a focused anomaly feed of users whose
behavior has drifted at medium severity or above.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus import ArgusEngine
from argus.api.dependencies import get_engine
from argus.dna import (
    BehavioralDNA,
    compute_similarity_score,
    detect_drift,
    dna_from_dict,
    get_signature,
)

router = APIRouter(prefix="/v1", tags=["dna"])

# Severity ordering for the medium+ anomaly filter.
_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class DNAResponse(BaseModel):
    """Full behavioral DNA response for a single user."""

    user_id: str
    confidence: float
    total_events: int
    similarity_score: float
    drift: dict
    signature: dict
    matrix: list[list[float]]
    current_week_matrix: list[list[float]]
    weekly_scores: list[float]
    last_updated: str


class DNASummaryRow(BaseModel):
    """One row in the cross-user DNA summary."""

    user_id: str
    confidence: float
    similarity_score: float
    drift_detected: bool
    drift_severity: str
    last_updated: str


class DNAAlertRow(BaseModel):
    """One row in the behavioral-anomaly feed."""

    user_id: str
    similarity_score: float
    drift_type: str | None
    drift_severity: str
    reason: str | None
    last_updated: str


def _all_dna_users(engine: ArgusEngine) -> list[str]:
    """Return all user IDs that have at least one scored event.

    Derived from recent alerts (LOW+), mirroring how the dashboard enumerates
    users. Users only get a DNA fingerprint once they have been scored, so this
    is the relevant population.
    """
    alerts = engine.get_recent_alerts(limit=500, min_risk_level="LOW")
    seen = {a["user_id"] for a in alerts if isinstance(a, dict) and "user_id" in a}
    return sorted(seen)


def _load_dna(engine: ArgusEngine, user_id: str) -> BehavioralDNA | None:
    """Load and deserialize a user's DNA, or None if absent."""
    stored = engine.store.get_dna(user_id)
    if not stored:
        return None
    return dna_from_dict(stored)


@router.get("/users/{user_id}/dna", response_model=DNAResponse)
def get_user_dna(
    user_id: str, engine: ArgusEngine = Depends(get_engine)
) -> DNAResponse:
    """Return the full behavioral DNA for a user.

    Responds with 404 if the user has no DNA profile yet.
    """
    dna = _load_dna(engine, user_id)
    if dna is None:
        raise HTTPException(
            status_code=404, detail=f"No behavioral DNA for user {user_id!r}"
        )

    return DNAResponse(
        user_id=dna.user_id,
        confidence=dna.confidence,
        total_events=dna.total_events,
        similarity_score=compute_similarity_score(dna),
        drift=detect_drift(dna),
        signature=get_signature(dna),
        matrix=dna.matrix,
        current_week_matrix=dna.current_week_matrix,
        weekly_scores=dna.weekly_scores,
        last_updated=dna.last_updated,
    )


@router.get("/dna/summary", response_model=list[DNASummaryRow])
def dna_summary(engine: ArgusEngine = Depends(get_engine)) -> list[DNASummaryRow]:
    """Return a DNA summary for all users, most-drifted (lowest similarity) first."""
    rows: list[DNASummaryRow] = []
    for user_id in _all_dna_users(engine):
        dna = _load_dna(engine, user_id)
        if dna is None:
            continue
        drift = detect_drift(dna)
        rows.append(
            DNASummaryRow(
                user_id=user_id,
                confidence=dna.confidence,
                similarity_score=compute_similarity_score(dna),
                drift_detected=drift["drift_detected"],
                drift_severity=drift["severity"],
                last_updated=dna.last_updated,
            )
        )

    rows.sort(key=lambda r: r.similarity_score)
    return rows


@router.get("/dna/alerts", response_model=list[DNAAlertRow])
def dna_alerts(engine: ArgusEngine = Depends(get_engine)) -> list[DNAAlertRow]:
    """Return users with drift at medium severity or above.

    These are behavioral anomalies caught by the DNA layer that rule-based
    scoring might have missed. Sorted by similarity ascending (worst first).
    """
    rows: list[DNAAlertRow] = []
    for user_id in _all_dna_users(engine):
        dna = _load_dna(engine, user_id)
        if dna is None:
            continue
        drift = detect_drift(dna)
        if _SEVERITY_ORDER.get(drift["severity"], 0) < _SEVERITY_ORDER["medium"]:
            continue
        rows.append(
            DNAAlertRow(
                user_id=user_id,
                similarity_score=drift["similarity_score"],
                drift_type=drift["drift_type"],
                drift_severity=drift["severity"],
                reason=drift["reason"],
                last_updated=dna.last_updated,
            )
        )

    rows.sort(key=lambda r: r.similarity_score)
    return rows
