# M8 — Observabilidade + LGPD: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Fechar o pilar de observabilidade (logs estruturados com mask PII, `/metrics` Prometheus, `/healthz` rico, OpenTelemetry traces, Sentry) e o último item LGPD (auto-particionamento mensal), deixando a stack pronta para o cutover do M9. Os endpoints LGPD de export/delete por cliente já existem do M6 — apenas serão verificados e documentados.

**Architecture:** Wiring transversal. Um único `services/logging_config.py` configura structlog (JSONRenderer em prod, ConsoleRenderer em dev) com `mask_pii` aplicado a todos os event values. Um único `services/otel_init.py` registra FastAPI/Celery/HTTPX/SQLAlchemy/Redis instrumentations quando `OTEL_EXPORTER_OTLP_ENDPOINT` está setado. Um único `services/sentry_init.py` chama `sentry_sdk.init` quando `SENTRY_DSN` está setado. Todos os 3 são wired em `main.py` (FastAPI lifespan) e em `workers/runtime.py` (via signal `worker_process_init`). Particionamento mensal vira tarefa Celery beat idempotente que roda diariamente.

**Tech Stack:** structlog (já presente), prometheus-client (já presente), sentry-sdk (novo), opentelemetry-sdk + instrumentations (novo), psycopg via asyncpg (existing), Grafana dashboards como JSON puro (importável).

**Pré-requisitos:** Tag `m7-pwa-tecnico`, CI verde, `infra/docker-compose.dev.yml` up.

**Out of scope (deferido para M9 ou pós-cutover):**
- Container Grafana de fato rodando (M8 só entrega dashboards JSON importáveis)
- Container Tempo/Jaeger rodando (M8 só prepara o cliente OTLP — endpoint configurável)
- Container Prometheus de fato scrapando (M8 só expõe `/metrics`)
- Fix do timing oracle em `/auth/login` (vai para M9 com o resto do hardening pré-cutover)

---

## File Structure

```
apps/api/
├── src/ondeline_api/
│   ├── services/
│   │   ├── logging_config.py        # NEW — structlog configure() + PII processor
│   │   ├── sentry_init.py           # NEW — sentry_sdk.init wrapper (no-op se DSN vazio)
│   │   └── otel_init.py             # NEW — OTel wrapper (no-op se endpoint vazio)
│   ├── api/
│   │   ├── metrics.py               # NEW — GET /metrics expondo REGISTRY
│   │   └── health.py                # MODIFY — /healthz com Celery queue depth
│   ├── workers/
│   │   ├── partition_jobs.py        # NEW — ensure_future_mensagens_partitions task
│   │   ├── runtime.py               # MODIFY — chama logging+sentry+otel em worker_process_init
│   │   └── beat_schedule.py         # MODIFY — adiciona schedule daily 02:30 do partition job
│   ├── main.py                      # MODIFY — chama logging+sentry+otel no startup
│   ├── config.py                    # MODIFY — adiciona otel_exporter_otlp_endpoint
│   └── observability/
│       └── celery_queue.py          # NEW — helper que mede queue depth no Redis broker
├── alembic/versions/
│   └── 0004_mensagens_partitions_2026_07_to_09.py   # NEW
├── tests/
│   ├── services/
│   │   ├── test_logging_config.py   # NEW
│   │   ├── test_sentry_init.py      # NEW
│   │   └── test_otel_init.py        # NEW
│   ├── api/
│   │   ├── test_metrics_endpoint.py # NEW
│   │   └── test_healthz_celery.py   # NEW
│   ├── workers/
│   │   └── test_partition_jobs.py   # NEW
│   └── observability/
│       └── test_celery_queue.py     # NEW
└── pyproject.toml                   # MODIFY — sentry-sdk + opentelemetry-*

infra/
├── docker-compose.dev.yml           # MODIFY — healthcheck próprio worker/beat
└── grafana/                         # NEW
    ├── README.md                    # como importar os dashboards
    └── dashboards/
        ├── ondeline-operational.json
        └── ondeline-product.json

docs/
└── runbooks/
    └── observability.md             # NEW — onde vê o quê (logs, metrics, traces, alerts)
```

---

## Tasks

### Task 1: structlog global config com PII mask processor

**Objetivo:** Existir um `configure_logging()` único, chamado no startup do FastAPI E no `worker_process_init` do Celery. Em produção: JSONRenderer + `mask_pii` aplicado recursivamente a todos os event values. Em dev/test: ConsoleRenderer colorido. Nível vem do `Settings.log_level`.

**Files:**
- Create: `apps/api/src/ondeline_api/services/logging_config.py`
- Create: `apps/api/tests/services/test_logging_config.py`
- Modify: `apps/api/src/ondeline_api/main.py` (chamar `configure_logging()` em `create_app()` antes de `FastAPI(...)`)
- Modify: `apps/api/src/ondeline_api/workers/runtime.py` (chamar `configure_logging()` em `worker_process_init`)

**Implementation:**

```python
# apps/api/src/ondeline_api/services/logging_config.py
"""Global structlog configuration with PII masking processor."""
from __future__ import annotations

import logging
from typing import Any

import structlog

from ondeline_api.config import get_settings
from ondeline_api.services.pii_mask import mask_pii


def _mask_pii_processor(
    _logger: Any, _method: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    """Recursively apply mask_pii() to all string values in the event dict."""
    return _walk(event_dict)  # type: ignore[return-value]


def _walk(value: Any) -> Any:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _walk(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_walk(v) for v in value)
    return value


_CONFIGURED = False


def configure_logging() -> None:
    """Configure structlog globally. Idempotent — safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _mask_pii_processor,
    ]
    if settings.env == "development":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True
```

```python
# apps/api/tests/services/test_logging_config.py (representative)
import io
import json
import logging

import pytest
import structlog

from ondeline_api.config import get_settings
from ondeline_api.services.logging_config import configure_logging, _walk


def _reset_structlog() -> None:
    structlog.reset_defaults()
    import ondeline_api.services.logging_config as mod
    mod._CONFIGURED = False


def test_mask_pii_walk_masks_cpf_in_nested_dict() -> None:
    out = _walk({"a": "cliente 123.456.789-00 ativo", "b": {"c": ["111.222.333-44"]}})
    assert "[CPF]" in out["a"]
    assert out["b"]["c"] == ["[CPF]"]


def test_mask_pii_walk_preserves_non_strings() -> None:
    assert _walk(42) == 42
    assert _walk(None) is None
    assert _walk(True) is True


def test_configure_logging_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_structlog()
    get_settings.cache_clear()
    configure_logging()
    configure_logging()  # second call must be no-op
    # If we got here without re-raising, idempotency holds.


def test_mask_pii_in_json_renderer_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _reset_structlog()
    monkeypatch.setenv("ENV", "production")
    get_settings.cache_clear()
    configure_logging()
    log = structlog.get_logger("test")
    log.info("event", email="joao@example.com", cpf_str="123.456.789-00")
    captured = capsys.readouterr().out
    # Last line is the JSON payload from our event
    line = [ln for ln in captured.splitlines() if "event" in ln][-1]
    payload = json.loads(line)
    assert payload["email"] == "[EMAIL]"
    assert payload["cpf_str"] == "[CPF]"
```

**Wire in `main.py`:**

```python
# Top of create_app(), before FastAPI(...)
from ondeline_api.services.logging_config import configure_logging
configure_logging()
```

**Wire in `workers/runtime.py`:** (verificar primeiro se já existe signal handler `worker_process_init`; senão adicionar)

```python
from celery.signals import worker_process_init
from ondeline_api.services.logging_config import configure_logging

@worker_process_init.connect
def _init_worker_process(**_kwargs: object) -> None:
    configure_logging()
```

**Run:**
```bash
cd apps/api && pytest tests/services/test_logging_config.py -v
```
Expected: 4 passing.

**Commit:** `feat(m8): add global structlog config with PII mask processor`

---

### Task 2: `/metrics` Prometheus endpoint

**Objetivo:** Expor o `REGISTRY` de `observability/metrics.py` via `GET /metrics`. CSRF-exempt. Content-Type `text/plain; version=0.0.4; charset=utf-8`. Inclui também métricas default do `prometheus_client` (process/python).

**Files:**
- Create: `apps/api/src/ondeline_api/api/metrics.py`
- Create: `apps/api/tests/api/test_metrics_endpoint.py`
- Modify: `apps/api/src/ondeline_api/main.py` (registrar router + adicionar `/metrics` a `CSRF_EXEMPT_PATHS`)
- Modify: `apps/api/src/ondeline_api/observability/metrics.py` (registrar `ProcessCollector` e `PlatformCollector` no REGISTRY)

**Implementation:**

```python
# apps/api/src/ondeline_api/api/metrics.py
"""GET /metrics — Prometheus exposition endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ondeline_api.observability.metrics import REGISTRY

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
```

**Modify `observability/metrics.py`** — adicionar process/platform collectors (no fim do arquivo):

```python
from prometheus_client import PlatformCollector, ProcessCollector

ProcessCollector(registry=REGISTRY)
PlatformCollector(registry=REGISTRY)
```

**Modify `main.py`:**
```python
from ondeline_api.api import metrics as metrics_router
# ...
CSRF_EXEMPT_PATHS = [
    "/auth/login", "/auth/refresh", "/auth/logout",
    "/webhook", "/healthz", "/livez", "/metrics", "/api/v1",
]
# ...
app.include_router(metrics_router.router)
```

```python
# apps/api/tests/api/test_metrics_endpoint.py
import pytest
from httpx import ASGITransport, AsyncClient

from ondeline_api.main import create_app
from ondeline_api.observability.metrics import webhook_received_total


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        webhook_received_total.inc()
        r = await client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "version=0.0.4" in r.headers["content-type"]
    body = r.text
    assert "ondeline_webhook_received_total" in body
    assert "process_cpu_seconds_total" in body  # ProcessCollector
    assert "python_info" in body  # PlatformCollector


@pytest.mark.asyncio
async def test_metrics_endpoint_is_csrf_exempt() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # No CSRF cookie/header — must still be 200
        r = await client.get("/metrics")
    assert r.status_code == 200
```

**Run:**
```bash
cd apps/api && pytest tests/api/test_metrics_endpoint.py -v
```
Expected: 2 passing.

**Commit:** `feat(m8): add /metrics Prometheus endpoint`

---

### Task 3: `/healthz` enriquecido + healthcheck próprio do worker e beat

**Objetivo (a):** `/healthz` adiciona campo `celery` com queue depth (counts dos lists Redis para `default`, `llm`, `sgp`, `notifications`). Continua devolvendo 503 se DB ou Redis falham; queues sempre OK (são informativas, não bloqueiam o status).

**Objetivo (b):** Override healthcheck do worker e beat no docker-compose pra parar de mostrar `unhealthy`. Worker: `celery -A ... inspect ping`. Beat: checa que o processo está vivo e o schedule file foi modificado nos últimos 2 min (atestando que o tick rodou).

**Files:**
- Create: `apps/api/src/ondeline_api/observability/celery_queue.py`
- Create: `apps/api/tests/observability/test_celery_queue.py`
- Create: `apps/api/tests/api/test_healthz_celery.py`
- Modify: `apps/api/src/ondeline_api/api/health.py`
- Modify: `infra/docker-compose.dev.yml`

**Implementation:**

```python
# apps/api/src/ondeline_api/observability/celery_queue.py
"""Measure Celery queue depth by reading Redis broker list lengths."""
from __future__ import annotations

from ondeline_api.deps import RedisLike

CELERY_QUEUES = ("default", "llm", "sgp", "notifications")


async def queue_depths(redis: RedisLike) -> dict[str, int]:
    """Return {queue_name: pending_task_count} for all configured queues.

    Celery 5 stores tasks in Redis as a LIST keyed by the queue name.
    LLEN returns 0 for missing keys, so unconfigured queues report cleanly.
    """
    depths: dict[str, int] = {}
    for q in CELERY_QUEUES:
        depths[q] = int(await redis.llen(q))
    return depths
```

```python
# apps/api/tests/observability/test_celery_queue.py
import pytest
from fakeredis.aioredis import FakeRedis

from ondeline_api.observability.celery_queue import CELERY_QUEUES, queue_depths


@pytest.mark.asyncio
async def test_queue_depths_returns_zero_for_empty_queues() -> None:
    redis = FakeRedis()
    depths = await queue_depths(redis)
    assert set(depths.keys()) == set(CELERY_QUEUES)
    assert all(v == 0 for v in depths.values())


@pytest.mark.asyncio
async def test_queue_depths_counts_pushed_messages() -> None:
    redis = FakeRedis()
    await redis.rpush("llm", b"task1", b"task2", b"task3")
    await redis.rpush("default", b"task1")
    depths = await queue_depths(redis)
    assert depths["llm"] == 3
    assert depths["default"] == 1
    assert depths["sgp"] == 0
    assert depths["notifications"] == 0
```

**Modify `api/health.py`** (substituir `/healthz`):

```python
from ondeline_api.observability.celery_queue import queue_depths


@router.get("/healthz")
async def healthz(
    response: Response,
    db: DBSessionLike = Depends(get_db),  # noqa: B008
    redis: RedisLike = Depends(get_redis),  # noqa: B008
) -> dict[str, Any]:
    checks: dict[str, str] = {}
    celery: dict[str, int] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    # Celery queue depth — informativo, não bloqueia status.
    try:
        celery = await queue_depths(redis)
    except Exception:
        celery = {}

    critical_ok = all(v == "ok" for v in checks.values())
    if not critical_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if critical_ok else "degraded",
        "checks": checks,
        "celery": celery,
    }
```

```python
# apps/api/tests/api/test_healthz_celery.py
import pytest
from httpx import ASGITransport, AsyncClient

from ondeline_api.main import create_app


@pytest.mark.asyncio
async def test_healthz_includes_celery_queues() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
    body = r.json()
    assert "celery" in body
    assert set(body["celery"].keys()) == {"default", "llm", "sgp", "notifications"}
    assert all(isinstance(v, int) for v in body["celery"].values())
```

**Modify `infra/docker-compose.dev.yml`** — adicionar a cada um dos services `worker` e `beat`:

```yaml
  worker:
    # ... (existente)
    healthcheck:
      test: ["CMD-SHELL", "celery -A ondeline_api.workers.celery_app:celery_app inspect ping -d celery@$$HOSTNAME || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  beat:
    # ... (existente)
    healthcheck:
      test: ["CMD-SHELL", "test -f /tmp/celerybeat-schedule && find /tmp/celerybeat-schedule -mmin -2 | grep -q ."]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
```

**Run:**
```bash
cd apps/api && pytest tests/observability/test_celery_queue.py tests/api/test_healthz_celery.py -v
# então:
docker compose -f infra/docker-compose.dev.yml up -d --build worker beat
sleep 60 && docker compose -f infra/docker-compose.dev.yml ps
```
Expected: worker e beat saem de `unhealthy` para `healthy`.

**Commit:** `feat(m8): enrich /healthz with celery queues + worker/beat healthchecks`

---

### Task 4: Sentry SDK init

**Objetivo:** Inicializar Sentry no startup do FastAPI e do Celery worker. No-op se `SENTRY_DSN` está vazio. PII scrubber custom usando `mask_pii` para garantir que strings em breadcrumbs/extras passem pelo mascarador.

**Files:**
- Modify: `apps/api/pyproject.toml` (adicionar `sentry-sdk[fastapi,celery]>=2.20.0`)
- Create: `apps/api/src/ondeline_api/services/sentry_init.py`
- Create: `apps/api/tests/services/test_sentry_init.py`
- Modify: `apps/api/src/ondeline_api/main.py`
- Modify: `apps/api/src/ondeline_api/workers/runtime.py`

**Implementation:**

```python
# apps/api/src/ondeline_api/services/sentry_init.py
"""Sentry SDK initialization (no-op when DSN is empty)."""
from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from ondeline_api.config import get_settings
from ondeline_api.services.pii_mask import mask_pii


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Apply mask_pii to message and breadcrumb messages before they leave the process."""
    if msg := event.get("message"):
        if isinstance(msg, str):
            event["message"] = mask_pii(msg)
    for crumb in event.get("breadcrumbs", {}).get("values", []) or []:
        if isinstance(crumb.get("message"), str):
            crumb["message"] = mask_pii(crumb["message"])
    return event


_INITIALIZED = False


def init_sentry(*, component: str) -> bool:
    """Initialize Sentry. Returns True if init ran, False if no-op.

    `component` is one of: "api" | "worker" | "beat". Used in tags.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return False
    settings = get_settings()
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.0,  # OTel handles traces; Sentry só pega erros
        send_default_pii=False,
        before_send=_before_send,
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
    )
    sentry_sdk.set_tag("component", component)
    _INITIALIZED = True
    return True
```

```python
# apps/api/tests/services/test_sentry_init.py
import pytest

from ondeline_api.config import get_settings
from ondeline_api.services import sentry_init as mod


def _reset() -> None:
    mod._INITIALIZED = False
    get_settings.cache_clear()


def test_init_sentry_noop_when_dsn_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("SENTRY_DSN", "")
    assert mod.init_sentry(component="api") is False


def test_init_sentry_runs_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    # Sentry accepts any valid-looking DSN even offline.
    monkeypatch.setenv("SENTRY_DSN", "https://abc@o0.ingest.sentry.io/0")
    assert mod.init_sentry(component="api") is True
    # Second call is idempotent — returns False
    assert mod.init_sentry(component="api") is False


def test_before_send_masks_pii_in_message() -> None:
    event = {
        "message": "user joao@example.com com CPF 123.456.789-00",
        "breadcrumbs": {"values": [
            {"message": "fetched 987.654.321-00"},
            {"message": "other"},
        ]},
    }
    out = mod._before_send(event, {})
    assert "[EMAIL]" in out["message"]
    assert "[CPF]" in out["message"]
    assert out["breadcrumbs"]["values"][0]["message"] == "fetched [CPF]"
```

**Wire em `main.py`** (depois de `configure_logging()`, antes de `FastAPI(...)`):
```python
from ondeline_api.services.sentry_init import init_sentry
init_sentry(component="api")
```

**Wire em `workers/runtime.py`** (no signal handler):
```python
from ondeline_api.services.sentry_init import init_sentry
# dentro de _init_worker_process(...)
init_sentry(component="worker")
```

**Update pyproject.toml** — adicionar à lista `dependencies`:
```
"sentry-sdk[fastapi,celery,sqlalchemy]>=2.20.0",
```

**Run:**
```bash
cd apps/api && pip install -e . && pytest tests/services/test_sentry_init.py -v
```
Expected: 3 passing.

**Commit:** `feat(m8): add sentry SDK initialization with PII scrubbing`

---

### Task 5: OpenTelemetry traces (FastAPI + Celery + HTTPX + SQLAlchemy + Redis)

**Objetivo:** Quando `OTEL_EXPORTER_OTLP_ENDPOINT` está setado, configura tracer provider, OTLPSpanExporter (HTTP), e instrumenta FastAPI, Celery, HTTPX, SQLAlchemy e Redis. No-op se variável vazia.

**Files:**
- Modify: `apps/api/pyproject.toml` (adicionar pacotes OTel)
- Modify: `apps/api/src/ondeline_api/config.py` (adicionar `otel_exporter_otlp_endpoint` e `otel_service_name`)
- Create: `apps/api/src/ondeline_api/services/otel_init.py`
- Create: `apps/api/tests/services/test_otel_init.py`
- Modify: `apps/api/src/ondeline_api/main.py`
- Modify: `apps/api/src/ondeline_api/workers/runtime.py`

**Dependencies to add to pyproject:**
```
"opentelemetry-sdk>=1.29.0",
"opentelemetry-exporter-otlp-proto-http>=1.29.0",
"opentelemetry-instrumentation-fastapi>=0.50b0",
"opentelemetry-instrumentation-celery>=0.50b0",
"opentelemetry-instrumentation-httpx>=0.50b0",
"opentelemetry-instrumentation-sqlalchemy>=0.50b0",
"opentelemetry-instrumentation-redis>=0.50b0",
```

**Add to Settings (`config.py`):**
```python
# Tracing (OpenTelemetry)
otel_exporter_otlp_endpoint: str = ""  # ex: http://tempo:4318
otel_service_name: str = "ondeline-api"
```

**Implementation:**

```python
# apps/api/src/ondeline_api/services/otel_init.py
"""OpenTelemetry initialization. No-op when OTLP endpoint is unset."""
from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ondeline_api.config import get_settings

_INITIALIZED = False


def init_otel(*, component: str, fastapi_app: Any = None) -> bool:
    """Initialize OTel tracing. Returns True if init ran, False if no-op.

    `component` is "api" | "worker" | "beat". `fastapi_app` is the FastAPI
    instance — required only when component == "api".
    """
    global _INITIALIZED
    if _INITIALIZED:
        # Idempotent — but if fastapi_app provided, still instrument it.
        if fastapi_app is not None:
            FastAPIInstrumentor.instrument_app(fastapi_app)
        return False

    settings = get_settings()
    if not settings.otel_exporter_otlp_endpoint:
        return False

    resource = Resource.create({
        SERVICE_NAME: f"{settings.otel_service_name}-{component}",
        "service.namespace": "ondeline",
        "deployment.environment": settings.env,
    })
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/traces"
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(enable_commenter=False)
    CeleryInstrumentor().instrument()

    if fastapi_app is not None:
        FastAPIInstrumentor.instrument_app(fastapi_app)

    _INITIALIZED = True
    return True
```

```python
# apps/api/tests/services/test_otel_init.py
import pytest

from ondeline_api.config import get_settings
from ondeline_api.services import otel_init as mod


def _reset() -> None:
    mod._INITIALIZED = False
    get_settings.cache_clear()


def test_init_otel_noop_when_endpoint_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert mod.init_otel(component="api") is False


def test_init_otel_runs_when_endpoint_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert mod.init_otel(component="worker") is True
    # Idempotent — second call no-op
    assert mod.init_otel(component="worker") is False
```

**Wire em `main.py`** (depois de `app = FastAPI(...)`, antes de `app.add_middleware(...)`):
```python
from ondeline_api.services.otel_init import init_otel
init_otel(component="api", fastapi_app=app)
```

**Wire em `workers/runtime.py`** (no signal handler):
```python
from ondeline_api.services.otel_init import init_otel
# dentro de _init_worker_process(...)
init_otel(component="worker")
```

**Run:**
```bash
cd apps/api && pip install -e . && pytest tests/services/test_otel_init.py -v
# E garantir que a suite inteira continua verde:
pytest -x
```
Expected: 2 OTel tests passing + suite inteira verde (instrumentações não devem quebrar nada quando endpoint vazio).

**Commit:** `feat(m8): add OpenTelemetry tracing for fastapi/celery/httpx/sqla/redis`

---

### Task 6: Auto-particionamento mensal de `mensagens`

**Objetivo (a):** Tarefa Celery `ensure_future_mensagens_partitions` que cria as próximas 3 partições mensais (idempotente — só cria se não existir). Roda daily 02:30 via beat.

**Objetivo (b):** Migration 0004 que cria imediatamente as partições 2026-07, 2026-08 e 2026-09 (sem esperar o beat rodar pela primeira vez).

**Files:**
- Create: `apps/api/alembic/versions/0004_mensagens_partitions_2026_07_to_09.py`
- Create: `apps/api/src/ondeline_api/workers/partition_jobs.py`
- Create: `apps/api/tests/workers/test_partition_jobs.py`
- Modify: `apps/api/src/ondeline_api/workers/beat_schedule.py`
- Modify: `apps/api/src/ondeline_api/workers/celery_app.py` (incluir o novo módulo em `include`)

**Migration 0004:**

```python
# apps/api/alembic/versions/0004_mensagens_partitions_2026_07_to_09.py
"""create mensagens partitions for 2026-07 through 2026-09

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PARTITIONS = [
    ("mensagens_2026_07", "2026-07-01", "2026-08-01"),
    ("mensagens_2026_08", "2026-08-01", "2026-09-01"),
    ("mensagens_2026_09", "2026-09-01", "2026-10-01"),
]


def upgrade() -> None:
    for name, start, end in _PARTITIONS:
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {name} PARTITION OF mensagens
            FOR VALUES FROM ('{start}') TO ('{end}')
        """)


def downgrade() -> None:
    for name, _, _ in reversed(_PARTITIONS):
        op.execute(f"DROP TABLE IF EXISTS {name}")
```

**Partition jobs:**

```python
# apps/api/src/ondeline_api/workers/partition_jobs.py
"""Celery task: ensure next 3 monthly mensagens partitions exist.

Runs daily at 02:30. Idempotent — uses CREATE TABLE IF NOT EXISTS.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import create_engine, text

from ondeline_api.config import get_settings

log = structlog.get_logger(__name__)


def _month_window(d: date) -> tuple[date, date]:
    """Return (first_day_of_month, first_day_of_next_month) for the month containing d."""
    start = d.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end


def _next_n_month_windows(today: date, n: int) -> list[tuple[str, date, date]]:
    """Return [(table_name, start, end), ...] for the next n months starting from `today`'s month."""
    windows: list[tuple[str, date, date]] = []
    cur = today.replace(day=1)
    for _ in range(n):
        start, end = _month_window(cur)
        table = f"mensagens_{start:%Y_%m}"
        windows.append((table, start, end))
        cur = end
    return windows


def ensure_partitions(today: date, n: int = 3) -> list[str]:
    """Create (idempotently) the next n monthly partitions. Returns list of table names."""
    settings = get_settings()
    sync_url = settings.database_url_sync or settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    created: list[str] = []
    try:
        with engine.connect() as conn:
            for table, start, end in _next_n_month_windows(today, n):
                conn.execute(text(
                    f"CREATE TABLE IF NOT EXISTS {table} "
                    f"PARTITION OF mensagens FOR VALUES FROM ('{start}') TO ('{end}')"
                ))
                created.append(table)
    finally:
        engine.dispose()
    return created


@shared_task(
    bind=True,
    name="ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions",
    queue="default",
)
def ensure_future_mensagens_partitions(self: Any) -> dict[str, Any]:
    try:
        created = ensure_partitions(today=datetime.now().date(), n=3)
        log.info("partition_job.completed", created=created)
        return {"created": created}
    except Exception as e:
        log.error("partition_job.failed", error=str(e), exc_info=True)
        raise
```

**Tests:**

```python
# apps/api/tests/workers/test_partition_jobs.py
from datetime import date

import pytest
from sqlalchemy import create_engine, text

from ondeline_api.workers.partition_jobs import (
    _next_n_month_windows,
    ensure_partitions,
)


def test_next_n_month_windows_handles_year_boundary() -> None:
    windows = _next_n_month_windows(date(2026, 11, 14), n=3)
    assert [w[0] for w in windows] == [
        "mensagens_2026_11",
        "mensagens_2026_12",
        "mensagens_2027_01",
    ]
    assert windows[0][1:] == (date(2026, 11, 1), date(2026, 12, 1))
    assert windows[1][1:] == (date(2026, 12, 1), date(2027, 1, 1))
    assert windows[2][1:] == (date(2027, 1, 1), date(2027, 2, 1))


def test_next_n_month_windows_uses_first_of_month() -> None:
    windows = _next_n_month_windows(date(2026, 7, 31), n=1)
    assert windows[0] == ("mensagens_2026_07", date(2026, 7, 1), date(2026, 8, 1))


@pytest.mark.integration
def test_ensure_partitions_is_idempotent(postgres_engine_sync) -> None:
    """Requires real Postgres. Skipped in unit suite via marker."""
    # Run twice; second call must not raise.
    created_first = ensure_partitions(today=date(2027, 3, 5), n=2)
    created_second = ensure_partitions(today=date(2027, 3, 5), n=2)
    assert created_first == created_second == [
        "mensagens_2027_03",
        "mensagens_2027_04",
    ]
    # Verify they exist
    with postgres_engine_sync.connect() as conn:
        rows = conn.execute(text(
            "SELECT relname FROM pg_class WHERE relname LIKE 'mensagens_2027_%' "
            "ORDER BY relname"
        )).all()
        names = [r[0] for r in rows]
        assert "mensagens_2027_03" in names
        assert "mensagens_2027_04" in names
```

> Nota: `postgres_engine_sync` é fixture já usada em outros testes integration. Se não existir, criar em `conftest.py` ou omitir o teste integration (deixar só os 2 unit tests do helper).

**Modify `beat_schedule.py`** — adicionar:
```python
"ensure-future-partitions": {
    "task": "ondeline_api.workers.partition_jobs.ensure_future_mensagens_partitions",
    "schedule": crontab(hour=2, minute=30),
},
```

**Modify `celery_app.py`** — adicionar `"ondeline_api.workers.partition_jobs"` à lista `include`.

**Run:**
```bash
cd apps/api && pytest tests/workers/test_partition_jobs.py -v -m "not integration"
# Aplicar migration:
alembic upgrade head
# Verificar:
psql -h localhost -p 5433 -U ondeline -d ondeline -c "\dt mensagens*"
```
Expected: unit tests passing; migration aplica; tabelas 2026-07 a 2026-09 visíveis.

**Commit:** `feat(m8): auto-create monthly mensagens partitions + migration 0004`

---

### Task 7: Grafana dashboards (artefatos JSON importáveis)

**Objetivo:** 2 dashboards JSON em `infra/grafana/dashboards/` prontos para importar manualmente em qualquer instância Grafana já existente. Não roda Grafana em compose — só prepara os artefatos. README explica como importar e quais data sources são esperados.

**Files:**
- Create: `infra/grafana/README.md`
- Create: `infra/grafana/dashboards/ondeline-operational.json`
- Create: `infra/grafana/dashboards/ondeline-product.json`

**Content `infra/grafana/README.md`:**

```markdown
# Grafana dashboards — Ondeline v2

Dois dashboards prontos para importar em qualquer Grafana com data source Prometheus.

## Data sources esperados
- **Prometheus** (UID: `prometheus`) — scrape de `http://api.ondeline:8000/metrics`

Job exemplo em `prometheus.yml`:
\`\`\`yaml
scrape_configs:
  - job_name: ondeline-api
    metrics_path: /metrics
    static_configs:
      - targets: ['api.ondeline:8000']
\`\`\`

## Como importar
1. Grafana UI → Dashboards → New → Import
2. Cole o conteúdo do JSON ou faça upload
3. Selecione a data source `prometheus` quando solicitado

## Dashboards

| Arquivo | Painéis |
|---|---|
| `ondeline-operational.json` | Webhook RPS, HMAC inválidos, rate-limited, dedup, msgs/min, evolution success/failure ratio, process CPU/memory |
| `ondeline-product.json` | OS abertas por status (placeholder até query DB ou export Postgres), msgs/min por role, taxa de envio Evolution OK |
```

**Conteúdo `ondeline-operational.json`** — JSON mínimo com 6 painéis (rate(counter), gauge process_resident_memory_bytes). Estrutura abreviada — copiar template de dashboard simples Grafana v10+. Painéis:

1. Webhooks recebidos (rate, 5min): `rate(ondeline_webhook_received_total[5m])`
2. Webhooks HMAC inválido: `rate(ondeline_webhook_invalid_signature_total[5m])`
3. Webhooks rate-limited: `rate(ondeline_webhook_rate_limited_total[5m])`
4. Mensagens processadas/min: `rate(ondeline_msgs_processed_total[1m]) * 60`
5. Dedup ratio: `rate(ondeline_msgs_dedup_total[5m]) / rate(ondeline_msgs_processed_total[5m])`
6. Evolution success rate: `rate(ondeline_evolution_send_total[5m]) / (rate(ondeline_evolution_send_total[5m]) + rate(ondeline_evolution_send_failure_total[5m]))`
7. Process memory: `process_resident_memory_bytes`
8. Process CPU: `rate(process_cpu_seconds_total[1m])`

**Conteúdo `ondeline-product.json`** — versão minimalista (KPIs reais virão de queries SQL, mas Grafana SQL plugin exige Postgres data source; ficaria fora do escopo M8). Por ora, esse arquivo terá apenas placeholders + comentário no painel apontando para `/api/v1/metricas` como fonte interim.

**Conteúdos JSON detalhados:** o agente que executa o plano deve gerar JSON Grafana v10 válido. Para evitar JSON de 200+ linhas inline no plano, gerar via template do Grafana export (definir UID `ondeline-operational`, title, schemaVersion 39, panels com targets PromQL acima, refresh `30s`, time range `now-1h`).

**Sanity check:**
```bash
python -c "import json; json.load(open('infra/grafana/dashboards/ondeline-operational.json'))"
python -c "import json; json.load(open('infra/grafana/dashboards/ondeline-product.json'))"
```
Expected: JSON parseia sem erro.

**Commit:** `feat(m8): add grafana dashboards (operational + product)`

---

### Task 8: Runbook + verify LGPD + CI + smoke + tag

**Objetivo:** Documentar o observability surface, verificar que LGPD export/delete já implementado em M6 continua funcionando, rodar CI completo, taggear `m8-observabilidade-lgpd`.

**Files:**
- Create: `docs/runbooks/observability.md`

**Conteúdo `docs/runbooks/observability.md`:**

```markdown
# Observability runbook — Ondeline v2

## Onde vê o quê

| Sinal | Endpoint / Lugar |
|---|---|
| Health | `GET /healthz` — DB + Redis + Celery queue depth |
| Liveness | `GET /livez` |
| Métricas | `GET /metrics` (Prometheus exposition format) |
| Logs | structlog JSON em stdout dos containers (api/worker/beat). PII (CPF/CNPJ/phone/email) mascarado automaticamente. |
| Traces | OpenTelemetry → endpoint configurável em `OTEL_EXPORTER_OTLP_ENDPOINT` (default vazio = desligado) |
| Erros | Sentry → `SENTRY_DSN` (default vazio = desligado) |

## Env vars de obs

| Var | Default | Significado |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nível structlog |
| `ENV` | `development` | `development` usa ConsoleRenderer; qualquer outro valor usa JSONRenderer |
| `SENTRY_DSN` | (vazio) | Se setado, ativa Sentry no api/worker/beat |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | (vazio) | Ex: `http://tempo:4318` — ativa OTel |
| `OTEL_SERVICE_NAME` | `ondeline-api` | Prefixo no `service.name` (sufixos: `-api`, `-worker`, `-beat`) |

## LGPD

| Operação | Endpoint / Job |
|---|---|
| Exportar dados de um cliente | `GET /api/v1/clientes/{id}/export` (admin) → ZIP com cliente.json + conversas.json + ordens_servico.json |
| Marcar cliente para purge | `DELETE /api/v1/clientes/{id}` (admin) → setа `deleted_at` e `retention_until = now + 30d` |
| Purge automático | `lgpd_purge_job` (Celery beat, daily 03:00) → hard-delete onde `retention_until < now` |
| Particionamento de `mensagens` | `ensure_future_mensagens_partitions` (Celery beat, daily 02:30) → cria próximas 3 partições idempotentemente |

## Healthcheck Docker

- `api` → `curl /livez` (a cada 10s)
- `worker` → `celery inspect ping -d celery@$HOSTNAME` (a cada 30s)
- `beat` → schedule file mtime < 2min (a cada 30s)
- `postgres`, `redis` → próprios

## Quando algo está errado

| Sintoma | O que checar |
|---|---|
| 503 em `/healthz` | Campo `checks.db` ou `checks.redis` mostra error |
| Worker `unhealthy` | `docker logs ondeline-worker` + `celery inspect active` |
| Filas crescendo (queue depth em `/healthz.celery`) | Worker scaled-down ou tarefa travada |
| Sem traces no Tempo | `OTEL_EXPORTER_OTLP_ENDPOINT` setado? Endpoint acessível do container? |
| Sem erros no Sentry | `SENTRY_DSN` setado? Sentry quota? |
```

**Verify LGPD (smoke manual):**
```bash
# Com API rodando + admin user (admin@admin.com / admin123, ver M2 seed):
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin123"}' \
  -c /tmp/cookies.txt -i

# Listar 1 cliente
curl http://localhost:8000/api/v1/clientes -b /tmp/cookies.txt | jq '.items[0].id' -r > /tmp/cliente_id

# Export ZIP
curl -O -J http://localhost:8000/api/v1/clientes/$(cat /tmp/cliente_id)/export -b /tmp/cookies.txt
unzip -l cliente-*.zip
```
Expected: ZIP contém cliente.json, conversas.json, ordens_servico.json, README.txt.

**Run smoke local:**
```bash
cd apps/api && pytest -x
cd ../dashboard && pnpm typecheck && pnpm lint && pnpm build
cd ../tecnico-pwa && pnpm typecheck && pnpm lint && pnpm build
```

**Push + watch CI (3 jobs verde):**
```bash
git push origin main
# Aguardar 3 jobs (api + dashboard + pwa) verdes
gh run watch
```

**Tag:**
```bash
git tag -a m8-observabilidade-lgpd -m "M8: Observability + LGPD

- Global structlog config with PII mask processor
- /metrics Prometheus endpoint
- /healthz enriched with Celery queue depth
- Worker/beat healthchecks (no more 'unhealthy')
- Sentry SDK wiring with PII scrubbing
- OpenTelemetry tracing (FastAPI + Celery + HTTPX + SQLAlchemy + Redis)
- Auto-monthly partitions for mensagens (migration 0004 + Celery beat job)
- Grafana dashboards (operational + product) as importable JSON
- Observability runbook"

git push origin m8-observabilidade-lgpd
```

**Commit:** `docs(m8): add observability runbook + tag m8-observabilidade-lgpd`

---

## Definition of Done

- [ ] `configure_logging()` chamado em api/worker/beat startup; PII mask aplicado a logs (verificável: log com CPF na request → linha JSON tem `[CPF]`)
- [ ] `GET /metrics` retorna 200 com Prometheus exposition (counters do código + ProcessCollector + PlatformCollector)
- [ ] `GET /healthz` retorna `celery: {default: 0, llm: 0, sgp: 0, notifications: 0}`
- [ ] `docker compose ps` mostra api/worker/beat todos `healthy` (não `unhealthy`)
- [ ] Sentry init no-op com DSN vazio; ativa com DSN setado (verificado por unit test)
- [ ] OTel init no-op com endpoint vazio; ativa com endpoint setado (verificado por unit test)
- [ ] Migration 0004 aplicada — `\dt mensagens*` mostra 2026-05 a 2026-09
- [ ] Celery beat tem job `ensure-future-partitions` na schedule
- [ ] `infra/grafana/dashboards/*.json` parseiam como JSON válido
- [ ] `docs/runbooks/observability.md` cobre logs/metrics/traces/errors/LGPD/healthcheck
- [ ] LGPD export ZIP funciona (smoke manual passa)
- [ ] CI 3 jobs verde
- [ ] Tag `m8-observabilidade-lgpd` pushed

---

## Self-Review (post-write)

**Spec coverage (§9 Observabilidade + §13 M8 entregável):**
- "Logs structlog + loguru, JSON, correlation_id, mascaramento PII" → Task 1 ✅ (loguru não usado — só structlog, consistente com o resto do código)
- "Métricas prometheus_client" → Task 2 ✅
- "Traces OpenTelemetry → Tempo" → Task 5 ✅ (endpoint configurável via env)
- "Erros Sentry" → Task 4 ✅
- "Dashboards Grafana" → Task 7 ✅ (JSON importável; container Grafana fica para infra prod)
- "Retenção/purge" → Já existe em M5 (`lgpd_purge_job`); verificado/documentado em Task 8 ✅
- "Export por cliente" → Já existe em M6 (`GET /clientes/{id}/export`); verificado em Task 8 ✅

**Decisão:** loguru mencionado na spec não é usado em parte alguma do código atual (M1-M7 usam só structlog). Não vou adicionar loguru — manter coerência.

**Placeholder scan:** Conteúdos dos 2 JSONs Grafana são descritos como template (Task 7) — o agente executor precisa gerar o JSON completo. Cabível porque o conteúdo é estrutural e gerar manualmente 200 linhas inline em um plano é mais ruído que sinal; especifiquei UIDs, painéis, queries PromQL.

**Type consistency:** Função `init_sentry(component=...)` e `init_otel(component=..., fastapi_app=...)` — assinaturas coerentes nos pontos de chamada (`main.py` passa `fastapi_app=app` só pro OTel; Sentry não precisa do app).

**Cobertura LGPD:** A spec menciona "retenção/purge + export por cliente + Sentry" como M8. Os dois primeiros já foram entregues em M5+M6 — Task 8 verifica e documenta, não reimplementa.
