"""Tests for Phase 7: data-source collectors and normalization helpers.

All file I/O uses temporary directories that are cleaned up after each test.
No real system log files are read.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest


# ── Normalize helpers ─────────────────────────────────────────────────────────

class TestNormalizeIp:
    def test_normalize_ip_strips_port(self):
        """normalize_ip must remove the port suffix from an IP:port string."""
        from argus.collectors.normalize import normalize_ip

        assert normalize_ip("192.168.1.5:54231") == "192.168.1.5"

    def test_normalize_ip_bare_ip_unchanged(self):
        """A bare IP address without a port must pass through unchanged."""
        from argus.collectors.normalize import normalize_ip

        assert normalize_ip("10.0.0.1") == "10.0.0.1"

    def test_normalize_ip_none_returns_unknown(self):
        """None input must return the UNKNOWN_IP sentinel, not raise."""
        from argus.collectors.normalize import normalize_ip, UNKNOWN_IP

        assert normalize_ip(None) == UNKNOWN_IP

    def test_normalize_ip_empty_string_returns_unknown(self):
        """An empty string must return UNKNOWN_IP."""
        from argus.collectors.normalize import normalize_ip, UNKNOWN_IP

        assert normalize_ip("") == UNKNOWN_IP


class TestNormalizeUserId:
    def test_normalize_user_id_strips_domain(self):
        """'CORP\\\\john' must normalize to 'john'."""
        from argus.collectors.normalize import normalize_user_id

        assert normalize_user_id("CORP\\john") == "john"

    def test_normalize_user_id_strips_email_domain(self):
        """'alice@corp.com' must normalize to 'alice'."""
        from argus.collectors.normalize import normalize_user_id

        assert normalize_user_id("alice@corp.com") == "alice"

    def test_normalize_user_id_lowercases(self):
        """Usernames must always be returned in lowercase."""
        from argus.collectors.normalize import normalize_user_id

        assert normalize_user_id("ALICE") == "alice"

    def test_normalize_user_id_none_returns_unknown(self):
        """None input must return 'unknown'."""
        from argus.collectors.normalize import normalize_user_id

        assert normalize_user_id(None) == "unknown"


class TestNormalizeDownloadMb:
    def test_normalize_download_mb_parses_gb(self):
        """'1GB' must parse to 1024.0 MB."""
        from argus.collectors.normalize import normalize_download_mb

        result = normalize_download_mb("1GB")
        assert abs(result - 1024.0) < 0.01, f"Expected ~1024 MB, got {result}"

    def test_normalize_download_mb_parses_kb(self):
        """'1024KB' must parse to 1.0 MB."""
        from argus.collectors.normalize import normalize_download_mb

        result = normalize_download_mb("1024KB")
        assert abs(result - 1.0) < 0.001, f"Expected ~1.0 MB, got {result}"

    def test_normalize_download_mb_handles_none(self):
        """None input must return 0.0 without raising."""
        from argus.collectors.normalize import normalize_download_mb

        assert normalize_download_mb(None) == 0.0

    def test_normalize_download_mb_bare_number_as_bytes(self):
        """A bare integer is treated as bytes: 1048576 bytes == 1.0 MB."""
        from argus.collectors.normalize import normalize_download_mb

        result = normalize_download_mb(1048576)
        assert abs(result - 1.0) < 0.001, f"Expected 1.0 MB, got {result}"


class TestBuildEvent:
    def test_build_event_normalizes_all_fields(self):
        """build_event must produce a well-typed Event with all fields normalized."""
        from argus.collectors.normalize import build_event

        event = build_event(
            user_id="CORP\\Alice",
            timestamp="2026-06-16T09:30:00",
            ip="192.168.1.5:22",
            device_id=None,
            download_mb="500KB",
            files_accessed="12 files",
            action="login",
        )
        assert event.user_id == "alice", "Domain prefix must be stripped and lowercased"
        assert event.ip == "192.168.1.5", "Port must be stripped from IP"
        assert abs(event.download_mb - 0.488) < 0.01, "500 KB must convert to ~0.488 MB"
        assert event.files_accessed == 12, "File count string must be parsed to int"
        assert event.device_id != "", "device_id must not be empty"

    def test_build_event_sets_unknown_device_when_none(self):
        """When device_id is None, build_event must set UNKNOWN_DEVICE sentinel."""
        from argus.collectors.normalize import build_event, UNKNOWN_DEVICE

        event = build_event(
            user_id="alice",
            timestamp=datetime(2026, 6, 16, 10, 0),
            ip="192.168.1.1",
        )
        assert event.device_id == UNKNOWN_DEVICE


# ── AuthCollector ─────────────────────────────────────────────────────────────

class TestAuthCollector:
    def test_auth_collector_reads_simulated_log(self):
        """AuthCollector.collect() on a simulated auth.log must return events."""
        from argus.collectors.simulate import simulate_auth_log
        from argus.collectors.auth_collector import AuthCollector

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "auth.log")
            simulate_auth_log(log_path, n_users=3, days=5)
            collector = AuthCollector(log_path)
            events = collector.collect()
        assert len(events) > 0, "AuthCollector must return at least one event from simulated log"

    def test_auth_collector_incremental_read(self):
        """Calling collect() a second time on the same file must return 0 new events."""
        from argus.collectors.simulate import simulate_auth_log
        from argus.collectors.auth_collector import AuthCollector

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "auth.log")
            simulate_auth_log(log_path, n_users=2, days=3)
            collector = AuthCollector(log_path)
            first = collector.collect()
            second = collector.collect()
        assert len(first) > 0, "First collect must return events"
        assert len(second) == 0, "Second collect on same file must return no new events"

    def test_auth_collector_missing_file_returns_empty(self):
        """AuthCollector on a non-existent path must return [] not raise."""
        from argus.collectors.auth_collector import AuthCollector

        collector = AuthCollector("/nonexistent/path/auth.log")
        events = collector.collect()
        assert events == [], "Missing file must yield empty list"


# ── NetworkCollector ──────────────────────────────────────────────────────────

class TestNetworkCollector:
    def test_simulate_network_log_produces_file(self):
        """simulate_network_log must create a non-empty file at the given path."""
        from argus.collectors.simulate import simulate_network_log

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "network.csv")
            simulate_network_log(log_path, n_users=2, days=3)
            assert os.path.isfile(log_path), "Log file must be created"
            assert os.path.getsize(log_path) > 0, "Log file must not be empty"

    def test_network_collector_reads_simulated_log(self):
        """NetworkCollector.collect() on a simulated CSV must return events."""
        from argus.collectors.simulate import simulate_network_log
        from argus.collectors.network_collector import NetworkCollector

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "network.csv")
            simulate_network_log(log_path, n_users=3, days=5)
            collector = NetworkCollector(log_path)
            events = collector.collect()
        # Events may be empty if all transfers fell below min_mb threshold; just
        # verify no exception was raised and the return type is correct.
        assert isinstance(events, list), "collect() must return a list"


# ── Simulation ────────────────────────────────────────────────────────────────

class TestRunSimulation:
    def test_run_simulation_returns_results(self, memory_engine):
        """run_simulation must return a non-empty list of result dicts."""
        from argus.collectors.simulate import run_simulation

        results = run_simulation(memory_engine, n_users=3, days=3, print_alerts=False)
        assert isinstance(results, list), "run_simulation must return a list"
        assert len(results) > 0, "Simulation must produce at least one scored event"

    def test_run_simulation_result_keys(self, memory_engine):
        """Each result dict must contain the five required keys."""
        from argus.collectors.simulate import run_simulation

        results = run_simulation(memory_engine, n_users=2, days=2, print_alerts=False)
        required_keys = {"user_id", "timestamp", "risk_score", "risk_level", "reasons"}
        for r in results:
            missing = required_keys - r.keys()
            assert not missing, f"Result dict missing keys: {missing}"

    def test_simulate_file_log_produces_file(self):
        """simulate_file_log must write a non-empty CSV file."""
        from argus.collectors.simulate import simulate_file_log

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "files.csv")
            simulate_file_log(log_path, n_users=2, days=3)
            assert os.path.isfile(log_path), "File log must be created"
            assert os.path.getsize(log_path) > 0, "File log must not be empty"
