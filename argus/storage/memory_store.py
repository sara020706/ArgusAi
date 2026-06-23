"""In-memory implementation of :class:`ArgusStore`.

Backed entirely by plain Python dicts and lists, this store keeps nothing on
disk. It is ideal for tests and for applications that already manage their own
persistence but still want Argus to cache profiles and recent events in
process.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from argus.schema import Event, ScoreResult
from argus.storage.base import RISK_LEVEL_ORDER, ArgusStore


class MemoryStore(ArgusStore):
    """A non-persistent :class:`ArgusStore` backed by in-process dicts."""

    def __init__(self):
        """Initialize empty profile and event containers."""
        self._profiles: dict[str, dict] = {}
        self._events: list[dict] = []

    def get_profile(self, user_id: str) -> dict | None:
        """Return a deep copy of the user's profile, or None. See base class."""
        profile = self._profiles.get(user_id)
        return copy.deepcopy(profile) if profile is not None else None

    def save_profile(self, user_id: str, profile: dict) -> None:
        """Store a deep copy of the profile under ``user_id``. See base class."""
        stored = copy.deepcopy(profile)
        # Normalize set-like fields to lists for a consistent serialized shape.
        stored["known_ips"] = list(stored.get("known_ips", []))
        stored["known_devices"] = list(stored.get("known_devices", []))
        self._profiles[user_id] = stored

    def log_event(self, event: Event, result: ScoreResult) -> None:
        """Append a scored-event dict to the in-memory log. See base class."""
        self._events.append(
            {
                "id": len(self._events) + 1,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "ip": event.ip,
                "device_id": event.device_id,
                "download_mb": event.download_mb,
                "files_accessed": event.files_accessed,
                "action": event.action,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "reasons": list(result.reasons),
                "rule_contributions": dict(result.rule_contributions),
                "stat_contributions": dict(result.stat_contributions),
            }
        )

    def get_recent_alerts(
        self, limit: int = 50, min_risk_level: str = "MEDIUM"
    ) -> list[dict]:
        """Return recent events at/above ``min_risk_level``. See base class."""
        min_rank = RISK_LEVEL_ORDER.get(min_risk_level, 0)
        filtered = [
            e
            for e in self._events
            if RISK_LEVEL_ORDER.get(e["risk_level"], 0) >= min_rank
        ]
        filtered.sort(key=lambda e: e["timestamp"], reverse=True)
        return [copy.deepcopy(e) for e in filtered[:limit]]

    def get_user_events(self, user_id: str, limit: int = 100) -> list[dict]:
        """Return recent events for one user, newest first. See base class."""
        filtered = [e for e in self._events if e["user_id"] == user_id]
        filtered.sort(key=lambda e: e["timestamp"], reverse=True)
        return [copy.deepcopy(e) for e in filtered[:limit]]

    def get_stats(self) -> dict:
        """Return system-wide statistics. See base class."""
        today = datetime.now(timezone.utc).date().isoformat()
        alerts_today = sum(
            1
            for e in self._events
            if e["risk_level"] in ("MEDIUM", "HIGH", "CRITICAL")
            and e["timestamp"][:10] == today
        )
        high_risk_users = sorted(
            {
                e["user_id"]
                for e in self._events
                if e["risk_level"] in ("HIGH", "CRITICAL")
            }
        )
        return {
            "total_events": len(self._events),
            "total_users": len(self._profiles),
            "alerts_today": alerts_today,
            "high_risk_users": high_risk_users,
        }
