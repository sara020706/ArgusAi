"""Tests for Phase 9: Behavioral DNA fingerprinting.

Covers the pure DNA functions, drift detection, serialization, the engine
integration, and the new API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from argus import ArgusEngine, Event
from argus.dna import (
    BehavioralDNA,
    compute_similarity_score,
    cosine_similarity,
    detect_drift,
    dna_from_dict,
    dna_to_dict,
    drift_to_score_bonus,
    flatten_matrix,
    get_active_days,
    get_peak_hours,
    get_signature,
    update_dna,
)
from argus.storage import MemoryStore


# ── Helpers ───────────────────────────────────────────────────────────────────

def _event_dict(user_id: str, dt: datetime) -> dict:
    """Build a minimal stored-event dict for a given timestamp."""
    return {
        "user_id": user_id,
        "timestamp": dt.isoformat(),
        "ip": "192.168.1.5",
        "device_id": "laptop-01",
        "download_mb": 45.0,
        "files_accessed": 18,
        "action": "login",
    }


def _consistent_dna(user_id: str = "john", weeks: int = 4) -> BehavioralDNA:
    """Build a DNA with a consistent 9-6 Mon-Fri pattern over several weeks.

    Uses 2026-06-01 (a Monday) as the base so weekday indices line up.
    """
    dna = BehavioralDNA(user_id)
    base = datetime(2026, 6, 1, 9, 0)  # Monday
    for week in range(weeks):
        for day in range(5):
            for hour in [9, 10, 11, 14, 15, 16]:
                dt = base + timedelta(weeks=week, days=day, hours=hour - 9)
                update_dna(dna, _event_dict(user_id, dt))
    return dna


# ── update_dna ──────────────────────────────────────────────────────────────

def test_update_dna_increments_counts():
    dna = BehavioralDNA("alice")
    dt = datetime(2026, 6, 1, 9, 0)  # Monday 09:00
    update_dna(dna, _event_dict("alice", dt))
    assert dna.raw_counts[0][9] == 1
    assert dna.total_events == 1


def test_update_dna_normalizes_matrix():
    dna = BehavioralDNA("alice")
    # Three events Monday 09:00, one event Monday 10:00
    for _ in range(3):
        update_dna(dna, _event_dict("alice", datetime(2026, 6, 1, 9, 0)))
    update_dna(dna, _event_dict("alice", datetime(2026, 6, 1, 10, 0)))
    # Max cell (Mon 09:00 = 3) normalizes to 1.0; Mon 10:00 (=1) to ~0.333
    assert dna.matrix[0][9] == pytest.approx(1.0)
    assert dna.matrix[0][10] == pytest.approx(1 / 3)
    # All values within 0..1
    assert all(0.0 <= v <= 1.0 for v in flatten_matrix(dna.matrix))


# ── cosine_similarity ────────────────────────────────────────────────────────

def test_cosine_similarity_identical_vectors_returns_1():
    a = [1.0, 2.0, 3.0, 4.0]
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_similarity_zero_vector_returns_1():
    # Zero vector means no data → no anomaly → 1.0
    assert cosine_similarity([0.0, 0.0, 0.0], [1.0, 2.0, 3.0]) == 1.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 1.0


def test_cosine_similarity_opposite_patterns():
    # Orthogonal vectors have zero similarity
    a = [1.0, 0.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


# ── compute_similarity_score ─────────────────────────────────────────────────

def test_compute_similarity_low_confidence_returns_1():
    dna = BehavioralDNA("alice")
    # A handful of events keeps confidence well below 0.2
    for _ in range(5):
        update_dna(dna, _event_dict("alice", datetime(2026, 6, 1, 9, 0)))
    assert dna.confidence < 0.2
    assert compute_similarity_score(dna) == 1.0


# ── detect_drift ──────────────────────────────────────────────────────────────

def test_detect_drift_no_drift():
    # Low confidence → drift detection skipped entirely
    dna = BehavioralDNA("alice")
    for _ in range(3):
        update_dna(dna, _event_dict("alice", datetime(2026, 6, 1, 9, 0)))
    drift = detect_drift(dna)
    assert drift["drift_detected"] is False
    assert drift["severity"] == "none"
    assert drift["reason"] is None


def test_detect_drift_sudden_drop():
    # Establish a consistent baseline, then a totally different current week.
    dna = _consistent_dna(weeks=4)
    assert dna.confidence >= 0.2

    # Overwrite the current week with an opposite pattern (weekend nights),
    # which is orthogonal to the weekday-daytime historical matrix.
    dna.current_week_counts = [[0] * 24 for _ in range(7)]
    for day in (5, 6):           # Sat, Sun
        for hour in (2, 3, 4):   # early morning
            dna.current_week_counts[day][hour] = 5
    from argus.dna import _normalize_matrix
    dna.current_week_matrix = _normalize_matrix(dna.current_week_counts)

    drift = detect_drift(dna)
    assert drift["drift_detected"] is True
    assert drift["similarity_score"] < 0.3
    assert drift["severity"] == "critical"


def test_detect_drift_severity_levels():
    # Drive specific similarity scores and assert the severity mapping bands.
    def _drift_for_similarity(target: float) -> dict:
        dna = BehavioralDNA("x", total_events=300, confidence=0.6)
        # Build hist and current vectors whose cosine similarity == target by
        # mixing a shared and an orthogonal component.
        import math
        theta = math.acos(max(-1.0, min(1.0, target)))
        # hist along axis 0; current at angle theta in the (0,1) plane
        hist = [[0.0] * 24 for _ in range(7)]
        curr = [[0.0] * 24 for _ in range(7)]
        hist[0][0] = 1.0
        curr[0][0] = math.cos(theta)
        curr[0][1] = math.sin(theta)
        dna.matrix = hist
        dna.current_week_matrix = curr
        return detect_drift(dna)

    assert _drift_for_similarity(0.95)["severity"] == "none"
    assert _drift_for_similarity(0.78)["severity"] == "low"
    assert _drift_for_similarity(0.60)["severity"] == "medium"
    assert _drift_for_similarity(0.40)["severity"] == "high"
    assert _drift_for_similarity(0.10)["severity"] == "critical"


def test_detect_drift_never_raises():
    # A malformed DNA must not raise — returns no-drift instead.
    dna = BehavioralDNA("x", confidence=0.5)
    dna.matrix = "garbage"  # type: ignore[assignment]
    drift = detect_drift(dna)
    assert drift["drift_detected"] is False
    assert drift["severity"] == "none"


# ── get_peak_hours / get_active_days ─────────────────────────────────────────

def test_get_peak_hours_correct():
    dna = _consistent_dna(weeks=4)
    assert get_peak_hours(dna) == [9, 10, 11, 14, 15, 16]


def test_get_active_days_correct():
    dna = _consistent_dna(weeks=4)
    # Base 2026-06-01 is a Monday; events span Mon-Fri.
    assert get_active_days(dna) == ["Mon", "Tue", "Wed", "Thu", "Fri"]


# ── drift_to_score_bonus ─────────────────────────────────────────────────────

def test_drift_to_score_bonus_critical():
    points, reason = drift_to_score_bonus({"severity": "critical"})
    assert points == 45.0
    assert "account takeover" in reason

    assert drift_to_score_bonus({"severity": "none"}) == (0.0, None)
    assert drift_to_score_bonus({"severity": "high"})[0] == 30.0
    assert drift_to_score_bonus({"severity": "medium"})[0] == 20.0
    assert drift_to_score_bonus({"severity": "low"})[0] == 10.0


# ── Serialization ─────────────────────────────────────────────────────────────

def test_dna_serialization_roundtrip():
    dna = _consistent_dna(weeks=4)
    sig_before = get_signature(dna)

    as_dict = dna_to_dict(dna)
    restored = dna_from_dict(as_dict)

    assert restored.user_id == dna.user_id
    assert restored.total_events == dna.total_events
    assert restored.confidence == dna.confidence
    assert restored.matrix == dna.matrix
    assert restored.current_week_matrix == dna.current_week_matrix
    assert restored.weekly_scores == dna.weekly_scores
    assert get_signature(restored) == sig_before


def test_dna_from_dict_handles_missing_keys():
    restored = dna_from_dict({"user_id": "bob"})
    assert restored.user_id == "bob"
    assert restored.total_events == 0
    assert len(restored.matrix) == 7
    assert len(restored.matrix[0]) == 24


def test_get_signature_shape():
    dna = _consistent_dna(weeks=4)
    sig = get_signature(dna)
    assert set(sig.keys()) == {
        "peak_hours", "active_days", "most_active_hour",
        "most_active_day", "activity_spread", "confidence",
    }
    assert isinstance(sig["activity_spread"], float)


# ── Engine integration ────────────────────────────────────────────────────────

def test_engine_updates_dna_on_score():
    engine = ArgusEngine(store=MemoryStore())
    base = datetime(2026, 6, 1, 9, 0)
    for i in range(10):
        engine.score(
            Event("alice", base + timedelta(hours=i), "192.168.1.5",
                  "laptop-01", 45.0, 18, "login")
        )
    dna = engine.get_dna("alice")
    assert dna is not None
    assert dna.total_events == 10
    assert isinstance(dna, BehavioralDNA)


def test_engine_get_dna_none_before_events():
    engine = ArgusEngine(store=MemoryStore())
    assert engine.get_dna("nobody") is None


def test_engine_dna_drift_adds_score():
    # Build a strong baseline, then score an off-pattern event and confirm the
    # DNA drift contribution is reflected once confidence is high enough.
    engine = ArgusEngine(store=MemoryStore())
    base = datetime(2026, 6, 1, 9, 0)  # Monday
    # ~120 events of consistent weekday-daytime behavior → confidence ~0.24
    for week in range(4):
        for day in range(5):
            for hour in [9, 10, 11, 14, 15, 16]:
                engine.score(
                    Event("john",
                          base + timedelta(weeks=week, days=day, hours=hour - 9),
                          "192.168.1.5", "laptop-01", 45.0, 18, "login")
                )
    dna = engine.get_dna("john")
    assert dna.confidence >= 0.2

    # New week with a radically different late-night pattern. The first event
    # archives the (matching) prior week and resets the current-week grid, so
    # drift only registers once the anomalous week has built up a few events.
    result = None
    for day in range(5):
        result = engine.score(
            Event("john", base + timedelta(weeks=4, days=day, hours=23),
                  "192.168.1.5", "laptop-01", 45.0, 18, "login")
        )
    # By now the current week diverges sharply from history → DNA contributes.
    assert "behavioral_dna" in result.stat_contributions
    assert result.stat_contributions["behavioral_dna"] > 0


# ── API endpoints ─────────────────────────────────────────────────────────────

def test_dna_api_endpoint_404_new_user(api_client):
    r = api_client.get("/v1/users/ghost/dna")
    assert r.status_code == 404


def test_dna_summary_endpoint(api_client):
    # Score a few events so at least one user has DNA. Spread across distinct
    # days so the unrelated correlation rapid-fire pattern doesn't trigger.
    for day in range(1, 6):
        api_client.post("/v1/events/score", json={
            "user_id": "alice",
            "timestamp": f"2026-06-0{day}T09:00:00",
            "ip": "192.168.1.10",
            "device_id": "laptop-01",
            "download_mb": 45.0,
            "files_accessed": 18,
            "action": "login",
        })
    r = api_client.get("/v1/dna/summary")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert any(row["user_id"] == "alice" for row in body)


def test_dna_endpoint_returns_matrix(api_client):
    for day in range(1, 6):
        api_client.post("/v1/events/score", json={
            "user_id": "alice",
            "timestamp": f"2026-06-0{day}T09:00:00",
            "ip": "192.168.1.10",
            "device_id": "laptop-01",
            "download_mb": 45.0,
            "files_accessed": 18,
            "action": "login",
        })
    r = api_client.get("/v1/users/alice/dna")
    assert r.status_code == 200
    body = r.json()
    assert len(body["matrix"]) == 7
    assert len(body["matrix"][0]) == 24
    assert "drift" in body
    assert "signature" in body


def test_explainer_handles_tuple_contributions(api_client):
    """Scoring several rapid events for one user triggers the correlation layer,
    which stores a ``(points, reason)`` tuple. The explainer must rank these
    without crashing (regression for the float-vs-tuple sort bug)."""
    last = None
    for hour in range(5):
        last = api_client.post("/v1/events/score", json={
            "user_id": "carol",
            "timestamp": f"2026-06-01T0{hour}:00:00",
            "ip": "10.0.0.9",
            "device_id": "laptop-09",
            "download_mb": 45.0,
            "files_accessed": 18,
            "action": "login",
        })
    assert last is not None
    assert last.status_code == 200
    body = last.json()
    assert body.get("risk_level") in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
