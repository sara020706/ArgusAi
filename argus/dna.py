"""Behavioral DNA Fingerprinting for Argus — Phase 9.

Every user gets a 7×24 behavioral matrix (days × hours) tracking when and
how intensely they work. A self-similarity score compares the current week's
pattern against the historical fingerprint using cosine similarity (0.0–1.0).

Sudden drop  → account takeover or insider threat.
Gradual drift → normal role change; update fingerprint.

Zero external dependencies — stdlib + math only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class BehavioralDNA:
    user_id: str
    # 7×24 grid — days (0=Mon) × hours (0-23)
    # each cell = normalized activity density 0.0-1.0
    matrix: list[list[float]] = field(
        default_factory=lambda: [[0.0] * 24 for _ in range(7)]
    )
    # raw event counts before normalization
    raw_counts: list[list[int]] = field(
        default_factory=lambda: [[0] * 24 for _ in range(7)]
    )
    total_events: int = 0
    confidence: float = 0.0       # 0.0-1.0, reaches 1.0 at 500 events
    last_updated: str = ""
    # weekly snapshots for trend (last 8 weeks)
    weekly_scores: list[float] = field(default_factory=list)
    current_week_matrix: list[list[float]] = field(
        default_factory=lambda: [[0.0] * 24 for _ in range(7)]
    )
    current_week_counts: list[list[int]] = field(
        default_factory=lambda: [[0] * 24 for _ in range(7)]
    )
    current_week_start: str = ""  # ISO date of the Monday that started the current week


# ── Helpers ───────────────────────────────────────────────────────────────────

def _week_start(dt: datetime) -> str:
    """Return ISO date string of the Monday starting the week containing dt."""
    monday = dt - timedelta(days=dt.weekday())
    return monday.date().isoformat()


def _normalize_matrix(raw: list[list[int]]) -> list[list[float]]:
    """Normalize a 7×24 raw-count grid so values are in 0.0–1.0."""
    max_val = max(raw[d][h] for d in range(7) for h in range(24))
    if max_val == 0:
        return [[0.0] * 24 for _ in range(7)]
    return [[raw[d][h] / max_val for h in range(24)] for d in range(7)]


def _event_timestamp(event) -> datetime | None:
    """Extract a datetime from an Event object or a stored event dict.

    Returns None if the timestamp cannot be parsed.
    """
    ts = None
    if isinstance(event, dict):
        ts = event.get("timestamp")
    else:
        ts = getattr(event, "timestamp", None)

    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None
    return None


# ── Core functions ────────────────────────────────────────────────────────────

def flatten_matrix(matrix: list[list[float]]) -> list[float]:
    """Flatten a 7×24 matrix to a 168-float list."""
    return [matrix[d][h] for d in range(7) for h in range(24)]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Standard cosine similarity between two flat vectors.

    Returns 1.0 for zero vectors (no data = no anomaly).
    """
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 1.0
    return dot / (mag_a * mag_b)


def update_dna(dna: BehavioralDNA, event) -> BehavioralDNA:
    """Update a BehavioralDNA with a new event.

    Accepts either an :class:`~argus.schema.Event` object or a stored event
    dict (as produced by ``ArgusStore.log_event``); both expose a ``timestamp``.

    Steps:
    - Detect week boundary (Monday); archive old week score if needed.
    - Increment raw_counts[day][hour] and current_week_counts.
    - Recompute normalized matrices.
    - Update confidence and last_updated.

    Update is O(1) apart from the fixed-size 7×24 normalization pass — no full
    history reprocessing.
    """
    dt = _event_timestamp(event)
    if dt is None:
        return dna

    day = dt.weekday()   # 0=Mon … 6=Sun
    hour = dt.hour
    week_start = _week_start(dt)

    # Week boundary: if the event belongs to a new week, archive the week that
    # just ended before resetting the current-week accumulators.
    if dna.current_week_start and dna.current_week_start != week_start:
        score = compute_similarity_score(dna) if dna.confidence >= 0.2 else 1.0
        dna.weekly_scores = (dna.weekly_scores + [round(score, 4)])[-8:]
        dna.current_week_counts = [[0] * 24 for _ in range(7)]
        dna.current_week_matrix = [[0.0] * 24 for _ in range(7)]

    if not dna.current_week_start or dna.current_week_start != week_start:
        dna.current_week_start = week_start

    # Increment counts
    dna.raw_counts[day][hour] += 1
    dna.current_week_counts[day][hour] += 1
    dna.total_events += 1

    # Recompute normalized matrices
    dna.matrix = _normalize_matrix(dna.raw_counts)
    dna.current_week_matrix = _normalize_matrix(dna.current_week_counts)

    # Derived fields
    dna.confidence = min(1.0, dna.total_events / 500)
    dna.last_updated = datetime.now(timezone.utc).isoformat()

    return dna


def compute_similarity_score(dna: BehavioralDNA) -> float:
    """Compare current_week_matrix against the historical matrix.

    Returns cosine similarity 0.0–1.0.
    Returns 1.0 if confidence < 0.2 (not enough history).
    """
    if dna.confidence < 0.2:
        return 1.0
    hist = flatten_matrix(dna.matrix)
    curr = flatten_matrix(dna.current_week_matrix)
    return cosine_similarity(hist, curr)


def detect_drift(dna: BehavioralDNA) -> dict:
    """Detect behavioral drift from the DNA fingerprint.

    Returns a dict with keys:
      drift_detected, similarity_score, drift_type, severity, reason

    Never raises — returns the no-drift result on any error.
    """
    no_drift: dict = {
        "drift_detected": False,
        "similarity_score": 1.0,
        "drift_type": None,
        "severity": "none",
        "reason": None,
    }

    try:
        if dna.confidence < 0.2:
            return no_drift

        score = compute_similarity_score(dna)

        # Severity mapping
        if score >= 0.85:
            severity = "none"
        elif score >= 0.70:
            severity = "low"
        elif score >= 0.50:
            severity = "medium"
        elif score >= 0.30:
            severity = "high"
        else:
            severity = "critical"

        drift_detected = severity != "none"
        drift_type: str | None = None
        reason: str | None = None

        if drift_detected:
            # Sudden: most recent archived weekly score dropped >0.4 vs now.
            if dna.weekly_scores:
                prev = dna.weekly_scores[-1]
                if prev - score > 0.4:
                    drift_type = "sudden"
                elif len(dna.weekly_scores) >= 3:
                    # Gradual: monotone downward trend over 3+ weeks, >0.15 total.
                    recent = dna.weekly_scores[-3:]
                    descending = all(
                        recent[i] >= recent[i + 1] for i in range(len(recent) - 1)
                    )
                    if descending and (recent[0] - score) > 0.15:
                        drift_type = "gradual"

            # Fallback classification when there is no weekly history to lean on:
            # a hard mismatch reads as sudden, a softer one as gradual.
            if drift_type is None:
                drift_type = "sudden" if severity in ("high", "critical") else "gradual"

            _, reason = drift_to_score_bonus({"severity": severity})

        return {
            "drift_detected": drift_detected,
            "similarity_score": round(score, 4),
            "drift_type": drift_type,
            "severity": severity,
            "reason": reason,
        }
    except Exception:
        return no_drift


def get_peak_hours(dna: BehavioralDNA) -> list[int]:
    """Return hours where the matrix average across days > 0.3, sorted ascending."""
    result = []
    for h in range(24):
        avg = sum(dna.matrix[d][h] for d in range(7)) / 7
        if avg > 0.3:
            result.append(h)
    return sorted(result)


def get_active_days(dna: BehavioralDNA) -> list[str]:
    """Return day names where the matrix average across hours > 0.1."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    result = []
    for d in range(7):
        avg = sum(dna.matrix[d][h] for h in range(24)) / 24
        if avg > 0.1:
            result.append(names[d])
    return result


def get_signature(dna: BehavioralDNA) -> dict:
    """Return a concise behavioral signature dict."""
    flat = flatten_matrix(dna.matrix)
    n = len(flat)

    if n == 0 or all(v == 0.0 for v in flat):
        return {
            "peak_hours": [],
            "active_days": [],
            "most_active_hour": 0,
            "most_active_day": "Mon",
            "activity_spread": 0.0,
            "confidence": round(dna.confidence, 4),
        }

    peak_hours = get_peak_hours(dna)
    active_days = get_active_days(dna)

    hour_avgs = [sum(dna.matrix[d][h] for d in range(7)) / 7 for h in range(24)]
    most_active_hour = hour_avgs.index(max(hour_avgs))

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_avgs = [sum(dna.matrix[d][h] for h in range(24)) / 24 for d in range(7)]
    most_active_day = day_names[day_avgs.index(max(day_avgs))]

    mean = sum(flat) / n
    variance = sum((v - mean) ** 2 for v in flat) / n
    activity_spread = math.sqrt(variance)

    return {
        "peak_hours": peak_hours,
        "active_days": active_days,
        "most_active_hour": most_active_hour,
        "most_active_day": most_active_day,
        "activity_spread": round(activity_spread, 4),
        "confidence": round(dna.confidence, 4),
    }


def drift_to_score_bonus(drift: dict) -> tuple[float, str | None]:
    """Convert a detect_drift result to an Argus score contribution.

    Returns (points, reason_string | None). Max 45 points (critical).
    """
    severity = drift.get("severity", "none")
    mapping = {
        "none":     (0.0,  None),
        "low":      (10.0, "Behavioral pattern slightly unusual"),
        "medium":   (20.0, "Behavioral drift detected"),
        "high":     (30.0, "Significant behavioral change"),
        "critical": (45.0, "Behavioral fingerprint mismatch — possible account takeover"),
    }
    return mapping.get(severity, (0.0, None))


def dna_to_dict(dna: BehavioralDNA) -> dict:
    """Serialize a BehavioralDNA to a JSON-safe dict."""
    return {
        "user_id": dna.user_id,
        "matrix": dna.matrix,
        "raw_counts": dna.raw_counts,
        "total_events": dna.total_events,
        "confidence": dna.confidence,
        "last_updated": dna.last_updated,
        "weekly_scores": dna.weekly_scores,
        "current_week_matrix": dna.current_week_matrix,
        "current_week_counts": dna.current_week_counts,
        "current_week_start": dna.current_week_start,
    }


def dna_from_dict(data: dict) -> BehavioralDNA:
    """Deserialize a BehavioralDNA from a dict. Missing keys fall back to defaults."""
    default_matrix = [[0.0] * 24 for _ in range(7)]
    default_counts = [[0] * 24 for _ in range(7)]

    return BehavioralDNA(
        user_id=data.get("user_id", ""),
        matrix=data.get("matrix") or default_matrix,
        raw_counts=data.get("raw_counts") or default_counts,
        total_events=data.get("total_events", 0),
        confidence=data.get("confidence", 0.0),
        last_updated=data.get("last_updated", ""),
        weekly_scores=data.get("weekly_scores") or [],
        current_week_matrix=data.get("current_week_matrix") or default_matrix,
        current_week_counts=data.get("current_week_counts") or default_counts,
        current_week_start=data.get("current_week_start", ""),
    )
