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
