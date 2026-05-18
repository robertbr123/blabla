"""FastAPI application factory."""
from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from ondeline_api import __version__
from ondeline_api.api import auth, health
from ondeline_api.api import metrics as metrics_router
from ondeline_api.api import webhook as webhook_router
from ondeline_api.api.v1 import canais as v1_canais
from ondeline_api.api.v1 import clientes as v1_clientes
from ondeline_api.api.v1 import config as v1_config
from ondeline_api.api.v1 import conversas as v1_conversas
from ondeline_api.api.v1 import conversas_stream as v1_conversas_stream
from ondeline_api.api.v1 import leads as v1_leads
from ondeline_api.api.v1 import manutencoes as v1_manutencoes
from ondeline_api.api.v1 import metricas as v1_metricas
from ondeline_api.api.v1 import ordens_servico as v1_os
from ondeline_api.api.v1 import planos as v1_planos
from ondeline_api.api.v1 import tecnico_me as v1_tecnico_me
from ondeline_api.api.v1 import tecnicos as v1_tecnicos
from ondeline_api.api.webhook import limiter as webhook_limiter
from ondeline_api.auth.csrf import CSRFMiddleware
from ondeline_api.config import get_settings
from ondeline_api.db.engine import get_sessionmaker
from ondeline_api.repositories.canal import CanalRepo
from ondeline_api.services.logging_config import configure_logging
from ondeline_api.services.otel_init import init_otel
from ondeline_api.services.sentry_init import init_sentry

_log = structlog.get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: garante canal default (F4) a partir de settings.evolution_instance."""
    settings = get_settings()
    try:
        sm = get_sessionmaker()
        async with sm() as session:
            async with session.begin():
                repo = CanalRepo(session)
                await repo.ensure_default(
                    slug="suporte",
                    nome="Suporte",
                    evolution_instance=settings.evolution_instance,
                )
        _log.info("startup.canal_default_ready", instance=settings.evolution_instance)
    except Exception as e:
        # Nao trava o startup se DB ainda nao estiver migrado — log apenas.
        _log.warning("startup.canal_default_failed", error=str(e))
    yield

CSRF_EXEMPT_PATHS = [
    "/auth/login",
    "/auth/refresh",
    "/auth/logout",
    "/webhook",
    "/healthz",
    "/livez",
    "/metrics",
    "/api/v1",
]


def create_app() -> FastAPI:
    configure_logging()
    init_sentry(component="api")
    settings = get_settings()
    app = FastAPI(
        title="Ondeline API",
        version=__version__,
        description="WhatsApp bot + admin API for Ondeline Telecom",
        lifespan=lifespan,
    )
    init_otel(component="api", fastapi_app=app)
    app.add_middleware(CSRFMiddleware, exempt_paths=CSRF_EXEMPT_PATHS)

    allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
    app.include_router(metrics_router.router)
    app.include_router(v1_conversas.router)
    app.include_router(v1_conversas_stream.router)
    app.include_router(v1_os.router)
    app.include_router(v1_leads.router)
    app.include_router(v1_clientes.router)
    app.include_router(v1_tecnicos.router)
    app.include_router(v1_tecnico_me.router)
    app.include_router(v1_manutencoes.router)
    app.include_router(v1_config.router)
    app.include_router(v1_metricas.router)
    app.include_router(v1_planos.router)
    app.include_router(v1_canais.router)
    return app


app = create_app()
