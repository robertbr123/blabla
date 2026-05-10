"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from ondeline_api import __version__
from ondeline_api.api import auth, health
from ondeline_api.api import webhook as webhook_router
from ondeline_api.api.webhook import limiter as webhook_limiter
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

    # Rate limiter (slowapi) — apenas o webhook usa por enquanto
    app.state.limiter = webhook_limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        from ondeline_api.observability.metrics import webhook_rate_limited_total

        webhook_rate_limited_total.inc()
        return JSONResponse({"detail": "rate limited"}, status_code=429)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(webhook_router.router)
    return app


app = create_app()
