"""SQLite-backed implementation of :class:`ArgusStore`.

This is the zero-setup default backend. It uses only the Python standard
library (``sqlite3`` and ``json``) and creates its tables automatically on
first use. ``known_ips``, ``known_devices`` and the various contribution dicts
are stored as JSON strings and parsed back on read.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from argus.schema import Event, ScoreResult
from argus.storage.base import RISK_LEVEL_ORDER, ArgusStore

_CREATE_PROFILES = """
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    avg_download_mb REAL,
    std_download_mb REAL,
    avg_files_accessed REAL,
    std_files_accessed REAL,
    known_ips TEXT,
    known_devices TEXT,
    event_count INTEGER,
    last_seen TEXT
)
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS scored_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    timestamp TEXT,
    ip TEXT,
    device_id TEXT,
    download_mb REAL,
    files_accessed INTEGER,
    action TEXT,
    risk_score REAL,
    risk_level TEXT,
    reasons TEXT,
    rule_contributions TEXT,
    stat_contributions TEXT
)
"""


class SQLiteStore(ArgusStore):
    """A persistent :class:`ArgusStore` backed by a SQLite database file."""

    def __init__(self, db_path: str = "argus.db"):
        """Initialize the store, creating the database and tables if needed.

        Args:
            db_path: Path to the SQLite database file. Defaults to
                ``"argus.db"`` in the current working directory. The special
                value ``":memory:"`` creates an ephemeral in-memory database.
        """
        self.db_path = db_path
        # check_same_thread=False so the same connection can serve a web server
        # worker pool; access is otherwise simple single-statement operations.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_CREATE_PROFILES)
        self._conn.execute(_CREATE_EVENTS)
        self._conn.commit()

    def get_profile(self, user_id: str) -> dict | None:
        """Retrieve a user's profile, parsing JSON columns. See base class."""
        row = self._conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "user_id": row["user_id"],
            "avg_download_mb": row["avg_download_mb"],
            "std_download_mb": row["std_download_mb"],
            "avg_files_accessed": row["avg_files_accessed"],
            "std_files_accessed": row["std_files_accessed"],
            "known_ips": json.loads(row["known_ips"] or "[]"),
            "known_devices": json.loads(row["known_devices"] or "[]"),
            "event_count": row["event_count"],
            "last_seen": row["last_seen"],
        }

    def save_profile(self, user_id: str, profile: dict) -> None:
        """Upsert a user profile, serializing list fields to JSON. See base."""
        self._conn.execute(
            """
            INSERT INTO user_profiles (
                user_id, avg_download_mb, std_download_mb,
                avg_files_accessed, std_files_accessed,
                known_ips, known_devices, event_count, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                avg_download_mb = excluded.avg_download_mb,
                std_download_mb = excluded.std_download_mb,
                avg_files_accessed = excluded.avg_files_accessed,
                std_files_accessed = excluded.std_files_accessed,
                known_ips = excluded.known_ips,
                known_devices = excluded.known_devices,
                event_count = excluded.event_count,
                last_seen = excluded.last_seen
            """,
            (
                user_id,
                profile.get("avg_download_mb", 0.0),
                profile.get("std_download_mb", 0.0),
                profile.get("avg_files_accessed", 0.0),
                profile.get("std_files_accessed", 0.0),
                json.dumps(list(profile.get("known_ips", []))),
                json.dumps(list(profile.get("known_devices", []))),
                profile.get("event_count", 0),
                profile.get("last_seen"),
            ),
        )
        self._conn.commit()

    def log_event(self, event: Event, result: ScoreResult) -> None:
        """Persist a scored event row. See base class."""
        self._conn.execute(
            """
            INSERT INTO scored_events (
                user_id, timestamp, ip, device_id, download_mb,
                files_accessed, action, risk_score, risk_level,
                reasons, rule_contributions, stat_contributions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.user_id,
                event.timestamp.isoformat(),
                event.ip,
                event.device_id,
                event.download_mb,
                event.files_accessed,
                event.action,
                result.risk_score,
                result.risk_level,
                json.dumps(result.reasons),
                json.dumps(result.rule_contributions),
                json.dumps(result.stat_contributions),
            ),
        )
        self._conn.commit()

    def _row_to_event_dict(self, row: sqlite3.Row) -> dict:
        """Convert a scored_events row into a parsed dict.

        Args:
            row: A ``sqlite3.Row`` from the ``scored_events`` table.

        Returns:
            A dict with JSON columns parsed back into Python objects.
        """
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "timestamp": row["timestamp"],
            "ip": row["ip"],
            "device_id": row["device_id"],
            "download_mb": row["download_mb"],
            "files_accessed": row["files_accessed"],
            "action": row["action"],
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
            "reasons": json.loads(row["reasons"] or "[]"),
            "rule_contributions": json.loads(row["rule_contributions"] or "{}"),
            "stat_contributions": json.loads(row["stat_contributions"] or "{}"),
        }

    def get_recent_alerts(
        self, limit: int = 50, min_risk_level: str = "MEDIUM"
    ) -> list[dict]:
        """Return recent events at/above ``min_risk_level``. See base class."""
        min_rank = RISK_LEVEL_ORDER.get(min_risk_level, 0)
        allowed = [
            level for level, rank in RISK_LEVEL_ORDER.items() if rank >= min_rank
        ]
        placeholders = ",".join("?" for _ in allowed)
        rows = self._conn.execute(
            f"""
            SELECT * FROM scored_events
            WHERE risk_level IN ({placeholders})
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (*allowed, limit),
        ).fetchall()
        return [self._row_to_event_dict(r) for r in rows]

    def get_user_events(self, user_id: str, limit: int = 100) -> list[dict]:
        """Return recent events for one user, newest first. See base class."""
        rows = self._conn.execute(
            """
            SELECT * FROM scored_events
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [self._row_to_event_dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Return system-wide statistics. See base class."""
        total_events = self._conn.execute(
            "SELECT COUNT(*) FROM scored_events"
        ).fetchone()[0]
        total_users = self._conn.execute(
            "SELECT COUNT(*) FROM user_profiles"
        ).fetchone()[0]

        today = datetime.now(timezone.utc).date().isoformat()
        alerts_today = self._conn.execute(
            """
            SELECT COUNT(*) FROM scored_events
            WHERE risk_level IN ('MEDIUM', 'HIGH', 'CRITICAL')
              AND substr(timestamp, 1, 10) = ?
            """,
            (today,),
        ).fetchone()[0]

        high_rows = self._conn.execute(
            """
            SELECT DISTINCT user_id FROM scored_events
            WHERE risk_level IN ('HIGH', 'CRITICAL')
            """
        ).fetchall()
        high_risk_users = [r["user_id"] for r in high_rows]

        return {
            "total_events": total_events,
            "total_users": total_users,
            "alerts_today": alerts_today,
            "high_risk_users": high_risk_users,
        }
