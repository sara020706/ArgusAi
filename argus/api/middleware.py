"""Authentication middleware for the Argus API.

:class:`APIKeyMiddleware` provides optional, header-based API-key auth. When the
``API_KEY`` environment variable is set, every request (except a small set of
public paths) must present a matching ``X-API-Key`` header. When it is unset,
authentication is disabled and the API is open.
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional ``X-API-Key`` authentication based on the ``API_KEY`` env var."""

    # Paths that never require authentication (health + docs).
    EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next):
        """Enforce the API key when configured, otherwise pass through.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The downstream response, or a 401 ``JSONResponse`` if a required
            API key is missing or incorrect.
        """
        configured_key = os.environ.get("API_KEY")

        # Auth disabled when no key is configured.
        if not configured_key:
            return await call_next(request)

        # Allow public paths through without a key.
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in self.EXCLUDED_PATHS):
            return await call_next(request)

        provided = request.headers.get("X-API-Key")
        if provided != configured_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
