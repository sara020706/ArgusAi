"""Shared engine wiring for the Argus API.

The API keeps a single process-wide :class:`~argus.ArgusEngine` instance.
:func:`initialize_engine` is called once at server startup (via the app's
lifespan handler) and :func:`get_engine` is the FastAPI dependency that routes
use to access it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from argus import ArgusEngine, IsolationForestDetector, ThreatIntelClient
from argus.storage import SQLiteStore

# Process-wide engine instance and a startup marker for uptime reporting.
_engine: ArgusEngine | None = None
_started_at: datetime | None = None


def get_engine() -> ArgusEngine:
    """FastAPI dependency returning the shared :class:`ArgusEngine`.

    Returns:
        The initialized engine.

    Raises:
        HTTPException: 503 if the engine has not been initialized yet.
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="Argus engine not initialized")
    return _engine


def get_started_at() -> datetime | None:
    """Return the UTC time the engine was initialized, or None.

    Returns:
        The startup timestamp, used for uptime metrics.
    """
    return _started_at


def get_uptime_seconds() -> float:
    """Return seconds elapsed since the engine was initialized.

    Returns:
        Uptime in seconds, or ``0.0`` if not yet initialized.
    """
    if _started_at is None:
        return 0.0
    return (datetime.now(timezone.utc) - _started_at).total_seconds()


def initialize_engine(
    db_path: str = "argus.db",
    abuseipdb_key: str | None = None,
    enable_ml: bool = False,
) -> ArgusEngine:
    """Initialize the process-wide :class:`ArgusEngine`.

    Called once at server startup. Builds a :class:`SQLiteStore` at ``db_path``,
    optionally attaches a threat-intel client and a trained ML detector, and
    stores the result for :func:`get_engine`.

    Args:
        db_path: Path to the SQLite database file. The special value
            ``":memory:"`` creates an ephemeral in-memory database (useful for
            tests).
        abuseipdb_key: Optional AbuseIPDB API key. If provided, a
            :class:`~argus.integrations.ThreatIntelClient` is attached.
        enable_ml: If ``True``, construct and train an
            :class:`~argus.IsolationForestDetector` on synthetic data.

    Returns:
        The initialized engine.
    """
    global _engine, _started_at

    store = SQLiteStore(db_path)

    threat_intel = None
    if abuseipdb_key:
        threat_intel = ThreatIntelClient(api_key=abuseipdb_key, store=store)

    detector = None
    if enable_ml:
        detector = IsolationForestDetector()

    engine = ArgusEngine(store=store, detector=detector, threat_intel=threat_intel)

    if enable_ml and detector is not None:
        # Train on synthetic data so the ML layer is usable immediately.
        engine.train()

    _engine = engine
    _started_at = datetime.now(timezone.utc)
    return engine


def reset_engine() -> None:
    """Reset the global engine state (primarily for testing)."""
    global _engine, _started_at
    _engine = None
    _started_at = None
