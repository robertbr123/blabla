from collections.abc import Iterator

import pytest
from ondeline_api.config import get_settings
from ondeline_api.services import otel_init as mod


def _reset() -> None:
    mod._INITIALIZED = False
    get_settings.cache_clear()


@pytest.fixture
def otel_cleanup() -> Iterator[None]:
    """Teardown that reverses every global side effect of init_otel.

    init_otel instruments SQLAlchemy/Redis/HTTPX/Celery process-globally and
    registers a TracerProvider with a BatchSpanProcessor pointed at the OTLP
    endpoint. Without teardown, subsequent tests in the same process run on
    an instrumented stack and the BatchSpanProcessor thread keeps retrying
    exports to an unreachable collector (visible in stderr at suite shutdown).

    This fixture reverses both effects after the test body runs.
    """
    yield
    from opentelemetry import trace
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    for instrumentor_cls in (
        CeleryInstrumentor,
        HTTPXClientInstrumentor,
        RedisInstrumentor,
        SQLAlchemyInstrumentor,
    ):
        try:
            instrumentor_cls().uninstrument()
        except Exception:
            # Idempotent — if the instrumentor wasn't registered (e.g. test
            # short-circuited before init), uninstrument may raise. Ignore.
            pass

    provider = trace.get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)
    if callable(shutdown):
        # Drains the BatchSpanProcessor synchronously; no more retry noise.
        shutdown()


def test_init_otel_noop_when_endpoint_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert mod.init_otel(component="api") is False


def test_init_otel_runs_when_endpoint_set(
    monkeypatch: pytest.MonkeyPatch, otel_cleanup: None
) -> None:
    _reset()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert mod.init_otel(component="worker") is True
    # Idempotent — second call no-op
    assert mod.init_otel(component="worker") is False
