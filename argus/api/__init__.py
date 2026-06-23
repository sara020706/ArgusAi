"""Argus REST API package.

Exposes the FastAPI application factory and the uvicorn runner.
"""

from argus.api.server import create_app, run

__all__ = ["create_app", "run"]
