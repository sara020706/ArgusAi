"""FastAPI application factory and server runner for Argus.

:func:`create_app` builds a configured :class:`fastapi.FastAPI` instance with
all routers mounted, CORS enabled, the optional API-key middleware installed,
and the shared engine initialized on startup. :func:`run` is a thin wrapper
that serves the app with uvicorn and is exposed as the ``argus-serve`` console
script.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argus.api import dependencies
from argus.api.dependencies import initialize_engine
from argus.api.middleware import APIKeyMiddleware
from argus.api.routes import alerts, events, health, users


def create_app(
    db_path: str = "argus.db",
    abuseipdb_key: str | None = None,
    enable_ml: bool = False,
    api_key: str | None = None,
) -> FastAPI:
    """Create and configure the Argus FastAPI application.

    Args:
        db_path: Path to the SQLite database file. ``":memory:"`` uses an
            ephemeral in-memory database.
        abuseipdb_key: Optional AbuseIPDB API key for the threat-intel layer.
        enable_ml: Whether to initialize and train the ML detector at startup.
        api_key: Optional API key. If provided, it is exported to the
            ``API_KEY`` environment variable so :class:`APIKeyMiddleware`
            enforces authentication.

    Returns:
        The configured :class:`fastapi.FastAPI` app with all routers mounted.
    """
    # If an API key is supplied here, make it visible to the middleware, which
    # reads it from the environment.
    if api_key:
        os.environ["API_KEY"] = api_key

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize the shared engine on startup if not already done."""
        # If the engine was already initialized at app-creation time (see
        # below), don't clobber it - this preserves any in-memory state and
        # avoids a redundant rebuild.
        if dependencies._engine is None:
            initialize_engine(
                db_path=db_path,
                abuseipdb_key=abuseipdb_key,
                enable_ml=enable_ml,
            )
        yield

    app = FastAPI(
        title="Argus",
        description="AI-powered insider threat detection API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Initialize the engine eagerly at app-creation time as well. The lifespan
    # handler above covers normal uvicorn serving (and reloads), but callers
    # that use the app without triggering lifespan events - notably
    # ``TestClient(app)`` used outside a ``with`` block - still get a ready
    # engine. With ``db_path=":memory:"`` a fresh in-memory DB is created here
    # and the lifespan re-init simply replaces it with another empty one.
    initialize_engine(
        db_path=db_path,
        abuseipdb_key=abuseipdb_key,
        enable_ml=enable_ml,
    )

    # CORS: allow all origins so the dashboard (different port) can call in.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Optional API-key authentication.
    app.add_middleware(APIKeyMiddleware)

    # Mount routers. The v1 prefixes live on the routers themselves; health and
    # metrics are unprefixed.
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(alerts.router)
    app.include_router(users.router)

    return app


def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    db_path: str = "argus.db",
    reload: bool = False,
) -> None:
    """Start the Argus API server with uvicorn.

    Args:
        host: Interface to bind to.
        port: Port to listen on.
        db_path: Path to the SQLite database file.
        reload: Whether to enable uvicorn auto-reload (development only).
    """
    import uvicorn

    app = create_app(db_path=db_path)
    uvicorn.run(app, host=host, port=port, reload=reload)
