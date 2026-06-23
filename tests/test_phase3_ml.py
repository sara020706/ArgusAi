"""Tests for Phase 3: synthetic data generator and IsolationForestDetector.

Scikit-learn is required for most tests. If it is not installed, the tests that
require it are skipped automatically via the ``sklearn`` mark.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest

sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")


class TestSyntheticGenerator:
    def test_synthetic_generator_produces_events(self):
        """generate_dataset must return a non-empty list of events and labels."""
        from argus.synthetic.generator import generate_dataset

        events, labels = generate_dataset(n_users=3, days=7)
        assert len(events) > 0, "Dataset must contain at least one event"
        assert len(labels) == len(events), "Labels list must match events list length"

    def test_synthetic_anomaly_rate(self):
        """With anomaly_rate=0.1, roughly 10% of labels must be True (±5% tolerance)."""
        from argus.synthetic.generator import generate_dataset

        events, labels = generate_dataset(n_users=5, days=14, anomaly_rate=0.1)
        if not labels:
            pytest.skip("No events generated")
        actual_rate = sum(labels) / len(labels)
        assert 0.05 <= actual_rate <= 0.15, (
            f"Anomaly rate {actual_rate:.2%} outside expected 5–15% window"
        )


class TestIsolationForestDetector:
    def _make_training_matrix(self, n: int = 200):
        """Generate a small feature matrix from synthetic events for training."""
        from argus.synthetic.generator import generate_dataset, events_to_feature_matrix
        from argus.profile import UserProfile

        events, _ = generate_dataset(n_users=5, days=30)
        per_user: dict = {}
        for event in events:
            up = per_user.setdefault(event.user_id, UserProfile(event.user_id))
            up.update(event)
        profiles = {uid: up.as_scoring_profile() for uid, up in per_user.items()}
        return events_to_feature_matrix(events, profiles)

    def test_isolation_forest_trains_without_error(self):
        """Calling train() on a feature matrix must set is_trained=True."""
        from argus.detectors import IsolationForestDetector

        detector = IsolationForestDetector()
        matrix = self._make_training_matrix()
        detector.train(matrix)
        assert detector.is_trained is True, "Detector must be trained after train()"

    def test_isolation_forest_scores_anomaly_higher(self, anomalous_event, sample_event):
        """After training, an anomalous event's ML score must exceed the normal event's."""
        from argus.detectors import IsolationForestDetector
        from argus.scorer import compute_score

        profile = {
            "avg_download_mb": 47.0, "std_download_mb": 12.0,
            "avg_files_accessed": 20.0, "std_files_accessed": 5.0,
            "known_ips": ["192.168.1.5"], "known_devices": ["work-laptop-01"],
        }
        detector = IsolationForestDetector()
        matrix = self._make_training_matrix()
        detector.train(matrix)

        anomalous_result = compute_score(anomalous_event, profile)
        normal_result = compute_score(sample_event, {
            **profile,
            "known_ips": ["192.168.1.10"],
            "known_devices": ["laptop-01"],
        })

        anomaly_score = detector.score(anomalous_result.raw_features)
        normal_score = detector.score(normal_result.raw_features)
        assert anomaly_score >= normal_score, (
            f"Anomaly ML score {anomaly_score:.3f} must be >= normal score {normal_score:.3f}"
        )

    def test_isolation_forest_graceful_without_training(self, anomalous_event):
        """Calling score() before train() must return 0.0 and not raise."""
        from argus.detectors import IsolationForestDetector
        from argus.scorer import compute_score

        detector = IsolationForestDetector()
        profile = {
            "avg_download_mb": 47.0, "std_download_mb": 12.0,
            "avg_files_accessed": 20.0, "std_files_accessed": 5.0,
            "known_ips": [], "known_devices": [],
        }
        result = compute_score(anomalous_event, profile)
        score = detector.score(result.raw_features)
        assert score == 0.0, "Untrained detector must return 0.0"

    def test_model_save_and_load(self, sample_event):
        """A trained model saved to disk and loaded in a fresh instance must score identically."""
        from argus.detectors import IsolationForestDetector
        from argus.scorer import compute_score

        profile = {
            "avg_download_mb": 47.0, "std_download_mb": 12.0,
            "avg_files_accessed": 20.0, "std_files_accessed": 5.0,
            "known_ips": ["192.168.1.10"], "known_devices": ["laptop-01"],
        }
        result = compute_score(sample_event, profile)

        detector1 = IsolationForestDetector()
        matrix = self._make_training_matrix()
        detector1.train(matrix)
        score1 = detector1.score(result.raw_features)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tf:
            path = tf.name
        try:
            detector1.save(path)

            detector2 = IsolationForestDetector()
            detector2.load(path)
            assert detector2.is_trained is True, "Loaded detector must be marked trained"
            score2 = detector2.score(result.raw_features)
            assert abs(score1 - score2) < 1e-9, (
                f"Scores differ after save/load: {score1:.6f} vs {score2:.6f}"
            )
        finally:
            os.unlink(path)
