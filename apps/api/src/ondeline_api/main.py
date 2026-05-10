"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

from ondeline_api import __version__
from ondeline_api.api import auth, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ondeline API",
        version=__version__,
        description="WhatsApp bot + admin API for Ondeline Telecom",
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
