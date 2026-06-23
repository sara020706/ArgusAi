"""HTTP client for the Argus REST API.

All functions are pure (no side effects beyond HTTP calls), have a 5-second
timeout, and return a safe empty fallback on any failure — they never raise.
The API base URL is read from the ``ARGUS_API_URL`` environment variable,
defaulting to ``http://localhost:8000``.
"""

from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = os.environ.get("ARGUS_API_URL", "http://localhost:8000").rstrip("/")
_TIMEOUT = 5


def _get(path: str, params: dict | None = None) -> Any:
    """Make a GET request to the Argus API.

    Args:
        path: Path relative to BASE_URL (e.g. ``"/health"``).
        params: Optional query-string parameters.

    Returns:
        Parsed JSON response, or ``None`` on any error.
    """
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, body: dict) -> Any:
    """Make a POST request to the Argus API.

    Args:
        path: Path relative to BASE_URL.
        body: JSON-serialisable request body.

    Returns:
        Parsed JSON response, or ``None`` on any error.
    """
    try:
        r = requests.post(f"{BASE_URL}{path}", json=body, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_health() -> dict:
    """Fetch the API health status.

    Returns:
        The health dict from ``GET /health``, or
        ``{"status": "unreachable"}`` if the request fails.
    """
    result = _get("/health")
    return result if isinstance(result, dict) else {"status": "unreachable"}


def score_event(event_dict: dict) -> dict | None:
    """Score a single event via the API.

    Args:
        event_dict: Event payload matching the ``EventRequest`` schema.

    Returns:
        The ``ScoreResponse`` dict, or ``None`` on failure.
    """
    result = _post("/v1/events/score", event_dict)
    return result if isinstance(result, dict) else None


def get_alerts(limit: int = 50, min_risk_level: str = "MEDIUM") -> list[dict]:
    """Fetch recent alerts from the API.

    Args:
        limit: Maximum number of alerts to return.
        min_risk_level: Minimum risk level filter (LOW/MEDIUM/HIGH/CRITICAL).

    Returns:
        List of alert dicts, or ``[]`` on failure.
    """
    result = _get("/v1/alerts", params={"limit": limit, "min_risk_level": min_risk_level})
    return result if isinstance(result, list) else []


def get_alert_stats() -> dict:
    """Fetch aggregate alert statistics.

    Returns:
        Stats dict from ``GET /v1/alerts/stats``, or ``{}`` on failure.
    """
    result = _get("/v1/alerts/stats")
    return result if isinstance(result, dict) else {}


def get_user_profile(user_id: str) -> dict | None:
    """Fetch a user's behavioral profile.

    Args:
        user_id: The user to look up.

    Returns:
        Profile dict, or ``None`` if not found or on failure.
    """
    result = _get(f"/v1/users/{user_id}/profile")
    return result if isinstance(result, dict) else None


def get_user_events(user_id: str, limit: int = 50) -> list[dict]:
    """Fetch recent events for a specific user.

    Args:
        user_id: The user to look up.
        limit: Maximum number of events to return.

    Returns:
        List of event dicts, newest first. ``[]`` on failure.
    """
    result = _get(f"/v1/users/{user_id}/events", params={"limit": limit})
    return result if isinstance(result, list) else []


def get_user_risk_summary(user_id: str) -> dict | None:
    """Fetch the risk summary for a user.

    Args:
        user_id: The user to look up.

    Returns:
        Risk summary dict, or ``None`` on failure or not found.
    """
    result = _get(f"/v1/users/{user_id}/risk_summary")
    return result if isinstance(result, dict) else None


def get_metrics() -> dict:
    """Fetch system-wide metrics.

    Returns:
        Metrics dict from ``GET /metrics``, or ``{}`` on failure.
    """
    result = _get("/metrics")
    return result if isinstance(result, dict) else {}


def get_all_users() -> list[str]:
    """Derive a sorted list of all user IDs seen in the system.

    Fetches up to 200 LOW+ alerts and extracts unique ``user_id`` values.
    This is an approximation — it only surfaces users who have at least one
    scored event stored.

    Returns:
        Sorted list of unique user ID strings, or ``[]`` on failure.
    """
    alerts = get_alerts(limit=200, min_risk_level="LOW")
    seen = {a["user_id"] for a in alerts if isinstance(a, dict) and "user_id" in a}
    return sorted(seen)


def get_user_dna(user_id: str) -> dict | None:
    """Fetch a user's behavioral DNA fingerprint.

    Args:
        user_id: The user to look up.

    Returns:
        The DNA dict from ``GET /v1/users/{id}/dna``, or ``None`` if not found
        or on failure.
    """
    result = _get(f"/v1/users/{user_id}/dna")
    return result if isinstance(result, dict) else None


def get_dna_summary() -> list[dict]:
    """Fetch the cross-user DNA summary, most-drifted first.

    Returns:
        List of summary dicts from ``GET /v1/dna/summary``, or ``[]`` on failure.
    """
    result = _get("/v1/dna/summary")
    return result if isinstance(result, list) else []


def get_dna_alerts() -> list[dict]:
    """Fetch users with behavioral drift at medium severity or above.

    Returns:
        List of anomaly dicts from ``GET /v1/dna/alerts``, or ``[]`` on failure.
    """
    result = _get("/v1/dna/alerts")
    return result if isinstance(result, list) else []
