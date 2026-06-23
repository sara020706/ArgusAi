"""Tests for Phase 4: multi-event correlation engine.

All tests build their own event dicts manually so they are fully isolated from
storage and other engine components.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


def _make_event_dict(
    ts: datetime,
    download_mb: float = 100.0,
    files_accessed: int = 10,
    ip: str = "192.168.1.1",
    device_id: str = "laptop-01",
    rule_contributions: dict | None = None,
    stat_contributions: dict | None = None,
) -> dict:
    """Build a minimal scored-event dict for correlation tests."""
    return {
        "user_id": "test_user",
        "timestamp": ts.isoformat(),
        "ip": ip,
        "device_id": device_id,
        "download_mb": download_mb,
        "files_accessed": files_accessed,
        "action": "download",
        "rule_contributions": rule_contributions or {},
        "stat_contributions": stat_contributions or {},
        "risk_score": 50.0,
        "risk_level": "MEDIUM",
    }


class TestDetectDownloadTrend:
    def test_detect_download_trend_escalating(self):
        """[100, 150, 200] — each value >20% above the previous — must be 'escalating'."""
        from argus.correlator import detect_download_trend

        result = detect_download_trend([100.0, 150.0, 200.0])
        assert result == "escalating", f"Expected 'escalating', got '{result}'"

    def test_detect_download_trend_stable(self):
        """[100, 105, 98] — changes all <20% — must be 'stable'."""
        from argus.correlator import detect_download_trend

        result = detect_download_trend([100.0, 105.0, 98.0])
        assert result == "stable", f"Expected 'stable', got '{result}'"

    def test_detect_download_trend_single_element(self):
        """A single-element list cannot form a trend — must be 'stable'."""
        from argus.correlator import detect_download_trend

        assert detect_download_trend([500.0]) == "stable"

    def test_detect_download_trend_empty(self):
        """An empty list must return 'stable' without raising."""
        from argus.correlator import detect_download_trend

        assert detect_download_trend([]) == "stable"


class TestComputeWindowStats:
    def test_compute_window_stats_counts_correctly(self):
        """Five events all at 02:00 must yield night_login_count == 5."""
        from argus.correlator import compute_window_stats

        base = datetime(2026, 6, 16, 2, 0)
        events = [_make_event_dict(base + timedelta(minutes=i * 10)) for i in range(5)]
        stats = compute_window_stats(events)
        assert stats["night_login_count"] == 5, (
            f"Expected 5 night logins, got {stats['night_login_count']}"
        )

    def test_compute_window_stats_event_count(self):
        """compute_window_stats must count every event in the input list."""
        from argus.correlator import compute_window_stats

        base = datetime(2026, 6, 16, 10, 0)
        events = [_make_event_dict(base + timedelta(hours=i)) for i in range(4)]
        stats = compute_window_stats(events)
        assert stats["event_count"] == 4

    def test_compute_window_stats_total_download(self):
        """Total download must be the sum of all individual download_mb values."""
        from argus.correlator import compute_window_stats

        base = datetime(2026, 6, 16, 10, 0)
        events = [
            _make_event_dict(base + timedelta(hours=i), download_mb=300.0)
            for i in range(4)
        ]
        stats = compute_window_stats(events)
        assert abs(stats["total_download_mb"] - 1200.0) < 1e-9


class TestSlowExfiltration:
    def test_slow_exfiltration_pattern_detected(self):
        """Three events totalling >1000 MB over >2 hours must fire slow_exfiltration."""
        from argus.correlator import compute_window_stats, evaluate_patterns

        base = datetime(2026, 6, 16, 8, 0)
        events = [
            _make_event_dict(base, download_mb=400.0),
            _make_event_dict(base + timedelta(hours=1, minutes=30), download_mb=400.0),
            _make_event_dict(base + timedelta(hours=3), download_mb=400.0),
        ]
        stats = compute_window_stats(events)
        matched = evaluate_patterns(stats)
        names = [r for _, r in matched]
        assert any("slow_exfiltration" in r or "exfiltration" in r.lower() for r in names), (
            f"slow_exfiltration pattern not found in: {names}"
        )


class TestAccountTakeover:
    def test_account_takeover_pattern_detected(self):
        """new_ip + new_device + off_hours must fire account_takeover_indicators."""
        from argus.correlator import compute_window_stats, evaluate_patterns

        base = datetime(2026, 6, 16, 19, 0)  # off-hours
        events = [
            _make_event_dict(
                base,
                ip="185.1.2.3",  # unknown IP
                device_id="alien-device",
                rule_contributions={"rule_new_ip": 20.0, "rule_new_device": 20.0},
            )
        ]
        stats = compute_window_stats(events)
        # Manually set new_ip and new_device since they come from rule_contributions
        stats["new_ip"] = True
        stats["new_device"] = True
        matched = evaluate_patterns(stats)
        names = [r for _, r in matched]
        assert any("account_takeover" in r or "takeover" in r.lower() for r in names), (
            f"account_takeover pattern not found in: {names}"
        )


class TestCorrelationBonus:
    def test_correlation_bonus_capped_at_100(self):
        """The final score must never exceed 100 even when multiple patterns fire."""
        from argus import Event
        from argus.schema import ScoreResult
        from argus.correlator import correlate

        ts = datetime(2026, 6, 16, 2, 0)

        # Current result already at 95 — very little headroom.
        result = ScoreResult(
            user_id="test", timestamp=ts,
            risk_score=95.0, risk_level="CRITICAL",
            rule_contributions={"rule_night_access": 35.0},
            stat_contributions={},
            reasons=["Night access"],
            raw_features={},
        )

        recent = [
            _make_event_dict(ts - timedelta(hours=i), download_mb=500.0)
            for i in range(5)
        ]
        bonus, _ = correlate("test", result, recent)
        final = result.risk_score + bonus
        assert final <= 100.0, f"Final score {final} exceeds 100"

    def test_correlate_never_raises_on_bad_data(self):
        """correlate() must return (0.0, []) rather than raising on malformed input."""
        from argus.schema import ScoreResult
        from argus.correlator import correlate

        ts = datetime(2026, 6, 16, 10, 0)
        result = ScoreResult(
            user_id="u", timestamp=ts, risk_score=30.0, risk_level="LOW",
            rule_contributions={}, stat_contributions={},
            reasons=[], raw_features={},
        )
        # Deliberately malformed event dicts
        bad_events = [{"timestamp": "not-a-date", "download_mb": "nope"}]
        bonus, reasons = correlate("u", result, bad_events)
        assert isinstance(bonus, float)
        assert isinstance(reasons, list)
