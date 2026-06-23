"""Tests for Phase 1: core feature extraction, rules, scorer, and explainer.

Every test is fully self-contained — no shared mutable state between tests.
"""

from __future__ import annotations

import json
import math
from datetime import datetime

import pytest


# ── Feature extraction ────────────────────────────────────────────────────────

class TestCyclicEncodeHour:
    def test_cyclic_encode_hour_continuity(self):
        """Hour 23 and hour 0 should be close in cyclic (sin/cos) space.

        A raw hour difference of 23 is maximal, but cyclically they are
        adjacent. The total L1 distance between their (sin, cos) projections
        must be below 0.3 to confirm the encoding wraps correctly.
        """
        from argus.features import cyclic_encode_hour

        sin_23, cos_23 = cyclic_encode_hour(23.0)
        sin_0, cos_0 = cyclic_encode_hour(0.0)
        distance = abs(sin_23 - sin_0) + abs(cos_23 - cos_0)
        assert distance < 0.3, f"Cyclic distance {distance:.4f} too large — encoding does not wrap"

    def test_cyclic_encode_noon_and_midnight_are_opposite(self):
        """Hour 0 and hour 12 should be exactly opposite on the unit circle.

        cos(0) ≈ 1 and cos(12) ≈ -1; sin values should both be near zero.
        """
        from argus.features import cyclic_encode_hour

        sin_0, cos_0 = cyclic_encode_hour(0.0)
        sin_12, cos_12 = cyclic_encode_hour(12.0)
        assert abs(cos_0 - 1.0) < 1e-9
        assert abs(cos_12 + 1.0) < 1e-9
        assert abs(sin_0) < 1e-9
        assert abs(sin_12) < 1e-9


class TestIsNightAccess:
    def test_is_night_access_boundaries(self):
        """Hours 0-5 inclusive are night; hour 6 and hour 23 are not.

        Tests the four boundary points: midnight (True), end-of-night (True),
        first non-night hour (False), and late evening (False).
        """
        from argus.features import is_night_access

        assert is_night_access(datetime(2026, 1, 1, 0, 0)) is True,  "00:00 is night"
        assert is_night_access(datetime(2026, 1, 1, 5, 59)) is True,  "05:59 is night"
        assert is_night_access(datetime(2026, 1, 1, 6, 0)) is False,  "06:00 is not night"
        assert is_night_access(datetime(2026, 1, 1, 23, 0)) is False, "23:00 is not night"


class TestIsOffHours:
    def test_is_off_hours_boundaries(self):
        """Working hours are 09:00-17:59 (9 inclusive, 18 exclusive).

        Hour 8 and hour 19 are off-hours; hours 9 and 17 are in-hours.
        """
        from argus.features import is_off_hours

        assert is_off_hours(datetime(2026, 1, 1, 8, 0)) is True,   "08:00 is off-hours"
        assert is_off_hours(datetime(2026, 1, 1, 9, 0)) is False,   "09:00 is in-hours"
        assert is_off_hours(datetime(2026, 1, 1, 17, 59)) is False,  "17:59 is in-hours"
        assert is_off_hours(datetime(2026, 1, 1, 18, 0)) is True,   "18:00 is off-hours"
        assert is_off_hours(datetime(2026, 1, 1, 19, 0)) is True,   "19:00 is off-hours"


class TestNormalizeDownload:
    def test_normalize_download_zero_std(self):
        """When std is zero, normalize_download must return 0.0 (no ZeroDivisionError)."""
        from argus.features import normalize_download

        result = normalize_download(100.0, 50.0, 0.0)
        assert result == 0.0, "Zero std must yield 0.0, not raise"

    def test_normalize_download_positive_zscore(self):
        """A download well above average should yield a positive z-score."""
        from argus.features import normalize_download

        z = normalize_download(200.0, 50.0, 30.0)
        assert z > 0, "Download above average must produce positive z-score"
        assert abs(z - 5.0) < 1e-9, "z = (200-50)/30 = 5.0"


class TestBuildFeatureVector:
    def test_build_feature_vector_keys(self, sample_event, mature_profile):
        """build_feature_vector must return all 13 expected feature keys."""
        from argus.features import build_feature_vector

        expected_keys = {
            "hour", "day_of_week", "is_weekend", "is_off_hours",
            "is_night_access", "hour_sin", "hour_cos",
            "download_mb", "files_accessed", "download_zscore",
            "files_zscore", "is_new_ip", "is_new_device",
        }
        fv = build_feature_vector(sample_event, mature_profile)
        missing = expected_keys - fv.keys()
        assert not missing, f"Feature vector missing keys: {missing}"


# ── Rules ─────────────────────────────────────────────────────────────────────

class TestRuleNightAccess:
    def test_rule_night_access_fires(self):
        """A 02:15 event must fire rule_night_access with points > 0 and a reason."""
        from argus.features import build_feature_vector
        from argus.rules import rule_night_access
        from argus import Event

        event = Event(
            user_id="test", timestamp=datetime(2026, 6, 16, 2, 15),
            ip="1.2.3.4", device_id="dev", download_mb=10, files_accessed=5,
            action="login",
        )
        profile = {
            "avg_download_mb": 50.0, "std_download_mb": 10.0,
            "avg_files_accessed": 10.0, "std_files_accessed": 3.0,
            "known_ips": ["1.2.3.4"], "known_devices": ["dev"],
        }
        fv = build_feature_vector(event, profile)
        points, reason = rule_night_access(fv)
        assert points > 0, "Night-access rule must fire at 02:15"
        assert reason is not None, "Fired rule must return a reason string"

    def test_rule_night_access_does_not_fire(self):
        """A 10:00 event must not trigger rule_night_access."""
        from argus.features import build_feature_vector
        from argus.rules import rule_night_access
        from argus import Event

        event = Event(
            user_id="test", timestamp=datetime(2026, 6, 16, 10, 0),
            ip="1.2.3.4", device_id="dev", download_mb=10, files_accessed=5,
            action="login",
        )
        profile = {
            "avg_download_mb": 50.0, "std_download_mb": 10.0,
            "avg_files_accessed": 10.0, "std_files_accessed": 3.0,
            "known_ips": ["1.2.3.4"], "known_devices": ["dev"],
        }
        fv = build_feature_vector(event, profile)
        points, reason = rule_night_access(fv)
        assert points == 0.0, "Night-access rule must not fire at 10:00"
        assert reason is None


class TestRuleLargeDownload:
    def test_rule_large_download_scales(self):
        """500 MB must score lower than 5000 MB — proportional scaling check."""
        from argus.rules import rule_large_download

        pts_500, _ = rule_large_download({"download_mb": 500.0})
        pts_5000, _ = rule_large_download({"download_mb": 5000.0})
        assert pts_500 == 0.0, "500 MB is below the 1000 MB threshold"
        assert pts_5000 > 0.0, "5000 MB must fire large-download rule"

    def test_rule_large_download_max_capped(self):
        """An astronomically large download must not exceed max_points (50)."""
        from argus.rules import rule_large_download

        pts, _ = rule_large_download({"download_mb": 1_000_000.0})
        assert pts <= 50.0, "Large-download rule points must never exceed max_points"


class TestEvaluateAllRules:
    def test_evaluate_all_rules_returns_only_fired(self):
        """A normal daytime event with known IP/device must return few or no fired rules."""
        from argus.rules import evaluate_all_rules

        fv = {
            "hour": 10.0, "day_of_week": 1.0, "is_weekend": False,
            "is_off_hours": False, "is_night_access": False,
            "hour_sin": 0.0, "hour_cos": 0.0,
            "download_mb": 50.0, "files_accessed": 10.0,
            "download_zscore": 0.1, "files_zscore": 0.1,
            "is_new_ip": False, "is_new_device": False,
        }
        fired = evaluate_all_rules(fv)
        for name, (pts, _) in fired.items():
            assert pts > 0, f"Rule {name} in fired dict but points == 0"


# ── Scorer ────────────────────────────────────────────────────────────────────

class TestScorer:
    def test_anomalous_event_scores_high(self, anomalous_event, mature_profile):
        """Anomalous event (night + 5 GB + new IP) against a mature profile must score > 60."""
        from argus.scorer import compute_score

        # Add new IP/device to trigger novelty rules
        result = compute_score(anomalous_event, mature_profile)
        assert result.risk_score > 60, (
            f"Expected risk_score > 60, got {result.risk_score}"
        )

    def test_normal_event_scores_low(self, sample_event, mature_profile):
        """Normal office-hours event against a mature profile must score < 50."""
        from argus.scorer import compute_score

        # Sample event uses the same IP as mature_profile's known IPs? No —
        # mature_profile has "192.168.1.5", sample_event has "192.168.1.10".
        # We seed known_ips to include the sample event's IP to keep it truly normal.
        profile = {**mature_profile, "known_ips": ["192.168.1.10"], "known_devices": ["laptop-01"]}
        result = compute_score(sample_event, profile)
        assert result.risk_score < 50, (
            f"Expected risk_score < 50 for normal event, got {result.risk_score}"
        )

    def test_score_capped_at_100(self):
        """The scorer must never produce a risk score above 100."""
        from argus.scorer import compute_score
        from argus import Event

        # Craft a worst-case event to maximize all rules simultaneously.
        worst = Event(
            user_id="worst", timestamp=datetime(2026, 6, 15, 1, 0),
            ip="8.8.8.8", device_id="alien-device", download_mb=50_000.0,
            files_accessed=5000, action="download",
        )
        profile = {
            "avg_download_mb": 10.0, "std_download_mb": 5.0,
            "avg_files_accessed": 5.0, "std_files_accessed": 2.0,
            "known_ips": [], "known_devices": [],
        }
        result = compute_score(worst, profile)
        assert result.risk_score <= 100.0, (
            f"Score {result.risk_score} exceeds 100"
        )

    def test_risk_level_bands(self):
        """get_risk_level must map scores to the correct categorical level."""
        from argus.scorer import get_risk_level

        assert get_risk_level(0) == "LOW"
        assert get_risk_level(15) == "LOW"
        assert get_risk_level(30) == "LOW"
        assert get_risk_level(31) == "MEDIUM"
        assert get_risk_level(45) == "MEDIUM"
        assert get_risk_level(60) == "MEDIUM"
        assert get_risk_level(61) == "HIGH"
        assert get_risk_level(70) == "HIGH"
        assert get_risk_level(85) == "HIGH"
        assert get_risk_level(86) == "CRITICAL"
        assert get_risk_level(90) == "CRITICAL"
        assert get_risk_level(100) == "CRITICAL"


# ── Explainer ─────────────────────────────────────────────────────────────────

class TestExplainer:
    def _make_result(self):
        """Build a ScoreResult fixture for explainer tests."""
        from argus.scorer import compute_score
        from argus import Event

        event = Event(
            user_id="john", timestamp=datetime(2026, 6, 16, 2, 15),
            ip="185.45.67.10", device_id="unknown-device-44",
            download_mb=5000.0, files_accessed=600, action="download",
        )
        profile = {
            "avg_download_mb": 47.0, "std_download_mb": 12.0,
            "avg_files_accessed": 20.0, "std_files_accessed": 5.0,
            "known_ips": ["192.168.1.5"], "known_devices": ["work-laptop-01"],
        }
        return compute_score(event, profile)

    def test_build_explanation_contains_user_id(self):
        """The explanation string must include the user_id of the scored event."""
        from argus.explainer import build_explanation

        result = self._make_result()
        explanation = build_explanation(result)
        assert result.user_id in explanation, "Explanation must mention the user_id"

    def test_build_explanation_contains_score(self):
        """The explanation string must include the numeric risk score."""
        from argus.explainer import build_explanation

        result = self._make_result()
        explanation = build_explanation(result)
        assert str(int(result.risk_score)) in explanation, (
            "Explanation must mention the risk score"
        )

    def test_summarize_result_is_json_serializable(self):
        """summarize_result must return a dict that passes json.dumps without error."""
        from argus.explainer import summarize_result

        result = self._make_result()
        summary = summarize_result(result)
        # Must not raise
        serialized = json.dumps(summary)
        assert isinstance(serialized, str) and len(serialized) > 0
