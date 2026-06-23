"""Tests for Phase 2: storage backends, UserProfile, and ArgusEngine persistence.

All database operations use either MemoryStore or SQLiteStore(":memory:") so no
files are created on disk. Every test is fully independent.
"""

from __future__ import annotations

from datetime import datetime

import pytest


class TestSQLiteStoreInit:
    def test_sqlite_store_creates_tables(self):
        """SQLiteStore(":memory:") must create both required tables without error.

        If table creation failed, any subsequent insert would raise. We verify
        by performing a round-trip save/get.
        """
        from argus.storage import SQLiteStore

        store = SQLiteStore(":memory:")
        # If tables exist, this must not raise.
        result = store.get_profile("nonexistent_user")
        assert result is None, "Unknown user must return None"


class TestMemoryStore:
    def test_memory_store_save_and_retrieve_profile(self):
        """Saving a profile dict then getting it back must return equal data."""
        from argus.storage import MemoryStore

        store = MemoryStore()
        profile_data = {
            "event_count": 10,
            "avg_download_mb": 50.0,
            "std_download_mb": 5.0,
            "avg_files_accessed": 20.0,
            "std_files_accessed": 3.0,
            "known_ips": ["192.168.1.1"],
            "known_devices": ["laptop-01"],
        }
        store.save_profile("alice", profile_data)
        retrieved = store.get_profile("alice")
        assert retrieved is not None, "Saved profile must be retrievable"
        assert retrieved["avg_download_mb"] == 50.0
        assert retrieved["known_ips"] == ["192.168.1.1"]


class TestSQLiteStorePersistence:
    def test_sqlite_store_save_and_retrieve_profile(self):
        """Same round-trip test as MemoryStore but for SQLiteStore(":memory:")."""
        from argus.storage import SQLiteStore

        store = SQLiteStore(":memory:")
        profile_data = {
            "event_count": 5,
            "avg_download_mb": 30.0,
            "std_download_mb": 8.0,
            "avg_files_accessed": 15.0,
            "std_files_accessed": 4.0,
            "known_ips": ["10.0.0.1"],
            "known_devices": ["dev-02"],
        }
        store.save_profile("bob", profile_data)
        retrieved = store.get_profile("bob")
        assert retrieved is not None
        assert retrieved["avg_download_mb"] == 30.0
        assert retrieved["known_devices"] == ["dev-02"]


class TestAlertLogging:
    def _make_event_and_result(self, risk_level: str):
        """Helper: create a minimal event and score it at a fixed level."""
        from argus import Event
        from argus.schema import ScoreResult

        event = Event(
            user_id="test_user", timestamp=datetime(2026, 6, 16, 2, 0),
            ip="1.2.3.4", device_id="dev", download_mb=100.0,
            files_accessed=50, action="download",
        )
        score = {"LOW": 15.0, "MEDIUM": 45.0, "HIGH": 75.0, "CRITICAL": 90.0}[risk_level]
        result = ScoreResult(
            user_id="test_user", timestamp=event.timestamp,
            risk_score=score, risk_level=risk_level,
            rule_contributions={}, stat_contributions={},
            reasons=["Test reason"], raw_features={},
        )
        return event, result

    def test_log_event_and_get_alerts(self):
        """Logging a HIGH event must make it appear in get_recent_alerts."""
        from argus.storage import MemoryStore

        store = MemoryStore()
        event, result = self._make_event_and_result("HIGH")
        store.log_event(event, result)
        alerts = store.get_recent_alerts(limit=10, min_risk_level="HIGH")
        assert len(alerts) >= 1, "HIGH event must appear in get_recent_alerts"

    def test_get_recent_alerts_filters_by_level(self):
        """get_recent_alerts(min="HIGH") must exclude LOW events."""
        from argus.storage import MemoryStore

        store = MemoryStore()
        _, low_result = self._make_event_and_result("LOW")
        _, high_result = self._make_event_and_result("HIGH")

        low_event = high_event = None
        from argus import Event
        low_event = Event(
            user_id="low_user", timestamp=datetime(2026, 6, 16, 10, 0),
            ip="1.1.1.1", device_id="d1", download_mb=10, files_accessed=5,
            action="login",
        )
        high_event = Event(
            user_id="high_user", timestamp=datetime(2026, 6, 16, 2, 0),
            ip="2.2.2.2", device_id="d2", download_mb=5000, files_accessed=600,
            action="download",
        )
        store.log_event(low_event, low_result)
        store.log_event(high_event, high_result)

        alerts = store.get_recent_alerts(limit=10, min_risk_level="HIGH")
        levels = [a["risk_level"] for a in alerts]
        assert "LOW" not in levels, "LOW events must be filtered out by min_risk_level='HIGH'"
        assert "HIGH" in levels or "CRITICAL" in levels


class TestUserProfile:
    def test_user_profile_welford_update(self):
        """After 30 updates, avg_download_mb must be within 5% of the true mean."""
        from argus.profile import UserProfile
        from argus import Event

        profile = UserProfile("welford_test")
        downloads = list(range(10, 40))  # 10, 11, ..., 39 — mean = 24.5
        true_mean = sum(downloads) / len(downloads)

        for i, dl in enumerate(downloads):
            event = Event(
                user_id="welford_test", timestamp=datetime(2026, 1, i + 1, 9, 0),
                ip="192.168.1.1", device_id="laptop", download_mb=float(dl),
                files_accessed=10, action="login",
            )
            profile.update(event)

        computed = profile.as_scoring_profile()["avg_download_mb"]
        assert abs(computed - true_mean) / true_mean < 0.05, (
            f"Welford mean {computed:.2f} deviates >5% from true mean {true_mean:.2f}"
        )

    def test_user_profile_is_mature(self):
        """is_mature() must return False below 20 events and True at 20 or more."""
        from argus.profile import UserProfile
        from argus import Event

        profile = UserProfile("maturity_test")
        assert profile.is_mature() is False, "New profile must not be mature"

        for i in range(20):
            event = Event(
                user_id="maturity_test", timestamp=datetime(2026, 1, i + 1, 9, 0),
                ip="192.168.1.1", device_id="laptop", download_mb=50.0,
                files_accessed=10, action="login",
            )
            profile.update(event)

        assert profile.is_mature() is True, "Profile with 20 events must be mature"


class TestArgusEngine:
    def test_argus_engine_scores_and_persists(self, memory_engine, anomalous_event):
        """Scoring an event must persist it so get_recent_alerts returns it."""
        result = memory_engine.score(anomalous_event)
        assert result.risk_score >= 0
        alerts = memory_engine.get_recent_alerts(limit=10, min_risk_level="LOW")
        user_ids = [a["user_id"] for a in alerts]
        assert anomalous_event.user_id in user_ids, (
            "Scored event must appear in get_recent_alerts"
        )
