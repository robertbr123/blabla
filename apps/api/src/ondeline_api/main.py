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
from ondeline_api.api import webhook_cloud as webhook_cloud_router
from ondeline_api.api.rate_limit import CpfExtractorMiddleware
from ondeline_api.api.v1 import canais as v1_canais
from ondeline_api.api.v1 import cliente_app_admin_chat as v1_cliente_app_admin_chat
from ondeline_api.api.v1 import cliente_app_auth as v1_cliente_app_auth
from ondeline_api.api.v1 import cliente_app_card_dia as v1_cliente_app_card_dia
from ondeline_api.api.v1 import cliente_app_chat as v1_cliente_app_chat
from ondeline_api.api.v1 import cliente_app_conexao as v1_cliente_app_conexao
from ondeline_api.api.v1 import cliente_app_contatos as v1_cliente_app_contatos
from ondeline_api.api.v1 import cliente_app_fidelidade as v1_cliente_app_fidelidade
from ondeline_api.api.v1 import cliente_app_indicacao as v1_cliente_app_indicacao
from ondeline_api.api.v1 import cliente_app_manutencoes as v1_cliente_app_manutencoes
from ondeline_api.api.v1 import cliente_app_me as v1_cliente_app_me
from ondeline_api.api.v1 import cliente_app_missoes as v1_cliente_app_missoes
from ondeline_api.api.v1 import cliente_app_notificacoes as v1_cliente_app_notificacoes
from ondeline_api.api.v1 import cliente_app_os as v1_cliente_app_os
from ondeline_api.api.v1 import cliente_app_promocoes as v1_cliente_app_promocoes
from ondeline_api.api.v1 import cliente_app_streak as v1_cliente_app_streak
from ondeline_api.api.v1 import clientes as v1_clientes
from ondeline_api.api.v1 import clientes_cadastro as v1_clientes_cadastro
from ondeline_api.api.v1 import config as v1_config
from ondeline_api.api.v1 import conversas as v1_conversas
from ondeline_api.api.v1 import conversas_stream as v1_conversas_stream
from ondeline_api.api.v1 import estoque as v1_estoque
from ondeline_api.api.v1 import indicacoes as v1_indicacoes
from ondeline_api.api.v1 import leads as v1_leads
from ondeline_api.api.v1 import manutencoes as v1_manutencoes
from ondeline_api.api.v1 import metricas as v1_metricas
from ondeline_api.api.v1 import ordens_servico as v1_os
from ondeline_api.api.v1 import planos as v1_planos
from ondeline_api.api.v1 import prompts as v1_prompts
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
    """Startup: garante canal default + diretorios de upload com permissao correta."""
    settings = get_settings()
    # Garante dirs de upload graváveis. Volumes docker às vezes vêm com owner
    # errado de deploy anterior — best-effort chmod 0o777 nas pastas-raiz.
    import os as _os
    from pathlib import Path as _P

    for d in [
        _P("/tmp/ondeline_os_fotos"),
        _P("/tmp/ondeline_cliente_fotos"),
        _P("/tmp/ondeline_promocoes"),
    ]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            try:
                _os.chmod(d, 0o777)
            except PermissionError:
                # Sem permissao pra chmod — provavelmente ja escrevemos mas
                # outro user dono. Robert precisa rodar:
                #   docker exec -u root blabla-api chmod -R 777 <path>
                _log.warning(
                    "startup.fotos_dir_chmod_failed",
                    path=str(d),
                    hint="run 'docker exec -u root <api> chmod -R 777 ' + path",
                )
        except Exception as e:
            _log.warning("startup.fotos_dir_init_failed", path=str(d), error=str(e))

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
    "/static",
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

    # Rate limiter (slowapi). Webhook usa IP; rotas /cliente-app/auth/* usam
    # CPF via CpfExtractorMiddleware + key_func custom (ver api/rate_limit.py).
    app.state.limiter = webhook_limiter
    app.add_middleware(CpfExtractorMiddleware)
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        from ondeline_api.observability.metrics import webhook_rate_limited_total

        webhook_rate_limited_total.inc()
        return JSONResponse({"detail": "rate limited"}, status_code=429)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(webhook_router.router)
    app.include_router(webhook_cloud_router.router)
    app.include_router(metrics_router.router)
    app.include_router(v1_conversas.router)
    app.include_router(v1_conversas_stream.router)
    app.include_router(v1_os.router)
    app.include_router(v1_leads.router)
    app.include_router(v1_clientes.router)
    app.include_router(v1_clientes_cadastro.router)
    app.include_router(v1_clientes_cadastro.sgp_router)
    app.include_router(v1_tecnicos.router)
    app.include_router(v1_tecnico_me.router)
    app.include_router(v1_manutencoes.router)
    app.include_router(v1_config.router)
    app.include_router(v1_metricas.router)
    app.include_router(v1_planos.router)
    app.include_router(v1_canais.router)
    app.include_router(v1_prompts.router)
    app.include_router(v1_estoque.router)
    app.include_router(v1_estoque.tecnico_estoque_router)
    app.include_router(v1_indicacoes.router)
    app.include_router(v1_cliente_app_auth.router)
    app.include_router(v1_cliente_app_me.router)
    app.include_router(v1_cliente_app_os.router)
    app.include_router(v1_cliente_app_os.admin_router)
    app.include_router(v1_cliente_app_chat.router)
    app.include_router(v1_cliente_app_admin_chat.admin_router)
    app.include_router(v1_cliente_app_promocoes.router)
    app.include_router(v1_cliente_app_promocoes.admin_router)
    app.include_router(v1_cliente_app_indicacao.router)
    app.include_router(v1_cliente_app_conexao.router)
    app.include_router(v1_cliente_app_notificacoes.router)
    app.include_router(v1_cliente_app_manutencoes.router)
    app.include_router(v1_cliente_app_contatos.router)
    app.include_router(v1_cliente_app_contatos.admin_router)
    app.include_router(v1_cliente_app_card_dia.router)
    app.include_router(v1_cliente_app_card_dia.admin_router)
    app.include_router(v1_cliente_app_streak.router)
    app.include_router(v1_cliente_app_missoes.router)
    app.include_router(v1_cliente_app_fidelidade.router)
    app.include_router(v1_cliente_app_fidelidade.admin_router)

    # Static dir pras imagens de promocoes (servido em /static/promocoes/...).
    # Usa /tmp pra evitar PermissionError no /app (user nao-root).
    from pathlib import Path as _Path

    from fastapi.staticfiles import StaticFiles

    _promo_dir = _Path("/tmp/ondeline_promocoes")
    try:
        _promo_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    app.mount(
        "/static/promocoes",
        StaticFiles(directory=str(_promo_dir)),
        name="static-promocoes",
    )
    return app


app = create_app()
