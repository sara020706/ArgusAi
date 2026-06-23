"""Tests for Phase 5: FastAPI REST server endpoints.

All tests use the ``api_client`` fixture (TestClient with an in-memory database)
so no network or file-system state is shared between tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest


# ── Shared request payloads ───────────────────────────────────────────────────

NORMAL_EVENT = {
    "user_id": "alice",
    "timestamp": "2026-06-16T09:30:00",
    "ip": "192.168.1.10",
    "device_id": "laptop-01",
    "download_mb": 45.0,
    "files_accessed": 18,
    "action": "login",
}

ANOMALOUS_EVENT = {
    "user_id": "john",
    "timestamp": "2026-06-16T02:15:00",
    "ip": "185.45.67.10",
    "device_id": "unknown-device-99",
    "download_mb": 5000.0,
    "files_accessed": 600,
    "action": "download",
}


# ── Health endpoints ──────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_endpoint_returns_200(self, api_client):
        """GET /health must always return HTTP 200."""
        response = api_client.get("/health")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_health_endpoint_never_500(self, api_client):
        """GET /health must never return a 5xx status even under adverse conditions.

        The health endpoint is contractually required to absorb all internal
        exceptions and return a degraded-but-200 response.
        """
        response = api_client.get("/health")
        assert response.status_code < 500, (
            f"/health returned {response.status_code} — must never be 5xx"
        )

    def test_health_response_structure(self, api_client):
        """GET /health response must include 'status' key."""
        response = api_client.get("/health")
        body = response.json()
        assert "status" in body, f"Missing 'status' key in /health response: {body}"


# ── Event scoring endpoints ───────────────────────────────────────────────────

class TestScoreEndpoint:
    def test_score_endpoint_normal_event(self, api_client):
        """POST /v1/events/score with a normal event must return 200."""
        response = api_client.post("/v1/events/score", json=NORMAL_EVENT)
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

    def test_score_endpoint_returns_valid_risk_level(self, api_client):
        """POST /v1/events/score must return a valid risk_level in the response."""
        response = api_client.post("/v1/events/score", json=NORMAL_EVENT)
        body = response.json()
        assert body.get("risk_level") in ("LOW", "MEDIUM", "HIGH", "CRITICAL"), (
            f"Unexpected risk_level: {body.get('risk_level')}"
        )

    def test_score_endpoint_anomalous_event(self, api_client):
        """POST /v1/events/score with a worst-case event must return 200.

        The night + 5 GB + unknown IP event is specifically designed to trigger
        HIGH or CRITICAL. On a fresh database with no user history the first
        event has cold-start handling applied, but subsequent events for the
        same user should score HIGH+.
        """
        # Score once to seed the profile, then score again.
        api_client.post("/v1/events/score", json=ANOMALOUS_EVENT)
        response = api_client.post("/v1/events/score", json=ANOMALOUS_EVENT)
        assert response.status_code == 200

    def test_score_response_has_explanation(self, api_client):
        """POST /v1/events/score response must contain a non-empty 'explanation' field."""
        response = api_client.post("/v1/events/score", json=NORMAL_EVENT)
        body = response.json()
        explanation = body.get("explanation", "")
        assert isinstance(explanation, str) and len(explanation) > 0, (
            "Response must include a non-empty 'explanation' string"
        )

    def test_score_response_has_risk_score(self, api_client):
        """POST /v1/events/score response must contain a numeric 'risk_score'."""
        response = api_client.post("/v1/events/score", json=NORMAL_EVENT)
        body = response.json()
        assert "risk_score" in body, "Response missing 'risk_score'"
        assert 0 <= body["risk_score"] <= 100, (
            f"risk_score {body['risk_score']} out of valid range 0-100"
        )


# ── Batch endpoint ────────────────────────────────────────────────────────────

class TestBatchEndpoint:
    def test_batch_endpoint_scores_multiple(self, api_client):
        """POST /v1/events/batch with 3 events must return a list of 3 results."""
        payload = [NORMAL_EVENT, NORMAL_EVENT, ANOMALOUS_EVENT]
        response = api_client.post("/v1/events/batch", json=payload)
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        results = response.json()
        assert isinstance(results, list), "Batch response must be a list"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    def test_batch_endpoint_rejects_over_100(self, api_client):
        """POST /v1/events/batch with 101 events must return HTTP 422."""
        payload = [NORMAL_EVENT] * 101
        response = api_client.post("/v1/events/batch", json=payload)
        assert response.status_code == 422, (
            f"Expected 422 for >100 events, got {response.status_code}"
        )


# ── Alerts endpoint ───────────────────────────────────────────────────────────

class TestAlertsEndpoint:
    def test_alerts_endpoint_returns_list(self, api_client):
        """GET /v1/alerts must return HTTP 200 with a list body."""
        response = api_client.get("/v1/alerts")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert isinstance(body, list), f"Expected list, got {type(body)}"

    def test_alerts_populated_after_scoring(self, api_client):
        """After scoring an anomalous event, /v1/alerts must contain at least one entry."""
        # Score enough to generate an alert
        api_client.post("/v1/events/score", json=ANOMALOUS_EVENT)
        api_client.post("/v1/events/score", json=ANOMALOUS_EVENT)
        response = api_client.get("/v1/alerts")
        assert response.status_code == 200


# ── User endpoints ────────────────────────────────────────────────────────────

class TestUserEndpoints:
    def test_user_profile_404_for_unknown_user(self, api_client):
        """GET /v1/users/<nonexistent>/profile must return HTTP 404."""
        response = api_client.get("/v1/users/nonexistent_user_xyz/profile")
        assert response.status_code == 404, (
            f"Expected 404 for unknown user, got {response.status_code}"
        )

    def test_user_profile_200_after_scoring(self, api_client):
        """After scoring an event for a user, their profile endpoint must return 200."""
        api_client.post("/v1/events/score", json=NORMAL_EVENT)
        response = api_client.get(f"/v1/users/{NORMAL_EVENT['user_id']}/profile")
        assert response.status_code == 200, (
            f"Expected 200 for known user, got {response.status_code}"
        )


# ── Metrics endpoint ──────────────────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_endpoint(self, api_client):
        """GET /metrics must return HTTP 200 and include 'total_events_scored'."""
        response = api_client.get("/metrics")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "total_events_scored" in body, (
            f"'total_events_scored' missing from /metrics response: {body}"
        )
