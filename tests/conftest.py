"""Shared pytest fixtures for all Argus test modules.

All fixtures are function-scoped (default) so every test starts with a clean,
independent state — no shared mutable objects between tests.
"""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.fixture
def memory_engine():
    """Return an ArgusEngine backed by an in-memory store.

    Uses MemoryStore so no database files are created or read. A fresh instance
    is created for each test, ensuring complete isolation.
    """
    from argus import ArgusEngine
    from argus.storage import MemoryStore

    return ArgusEngine(store=MemoryStore())


@pytest.fixture
def sample_event():
    """Return a normal weekday office-hours event — should score LOW.

    Tuesday 09:30, known IP range, modest download, reasonable file count.
    """
    from argus import Event

    return Event(
        user_id="alice",
        timestamp=datetime(2026, 6, 16, 9, 30),
        ip="192.168.1.10",
        device_id="laptop-01",
        download_mb=45.0,
        files_accessed=18,
        action="login",
    )


@pytest.fixture
def anomalous_event():
    """Return a classic insider-threat event — should score HIGH or CRITICAL.

    Night login (02:15), massive 5 GB download, 600 files, unknown external IP,
    and an unrecognized device. All major rules and stat signals should fire.
    """
    from argus import Event

    return Event(
        user_id="john",
        timestamp=datetime(2026, 6, 16, 2, 15),
        ip="185.45.67.10",
        device_id="unknown-device-99",
        download_mb=5000.0,
        files_accessed=600,
        action="download",
    )


@pytest.fixture
def blank_profile():
    """Return an empty user-profile dict for a brand-new user with no history."""
    return {
        "avg_download_mb": 0.0,
        "std_download_mb": 0.0,
        "avg_files_accessed": 0.0,
        "std_files_accessed": 0.0,
        "known_ips": [],
        "known_devices": [],
    }


@pytest.fixture
def mature_profile():
    """Return a realistic user-profile dict for an established office user.

    Baseline: ~47 MB downloads, ~20 files, known IP and device. Used to verify
    that the statistical layer can produce a meaningful z-score deviation when
    an anomalous event is scored against it.
    """
    return {
        "avg_download_mb": 47.0,
        "std_download_mb": 12.0,
        "avg_files_accessed": 20.0,
        "std_files_accessed": 5.0,
        "known_ips": ["192.168.1.5"],
        "known_devices": ["work-laptop-01"],
    }


@pytest.fixture
def api_client():
    """Return a FastAPI TestClient with an in-memory database.

    The app is created with ``db_path=":memory:"`` so each test gets a fresh,
    ephemeral database. No server process is started — requests are handled
    in-process via Starlette's TestClient.
    """
    from argus.api.server import create_app
    from fastapi.testclient import TestClient

    app = create_app(db_path=":memory:")
    return TestClient(app)
