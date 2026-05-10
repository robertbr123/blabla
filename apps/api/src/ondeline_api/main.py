"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from ondeline_api import __version__
from ondeline_api.api import auth, health
from ondeline_api.auth.csrf import CSRFMiddleware

CSRF_EXEMPT_PATHS = [
    "/auth/login",
    "/auth/refresh",
    "/auth/logout",
    "/webhook",
    "/healthz",
    "/livez",
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ondeline API",
        version=__version__,
        description="WhatsApp bot + admin API for Ondeline Telecom",
    )
    app.add_middleware(CSRFMiddleware, exempt_paths=CSRF_EXEMPT_PATHS)
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
