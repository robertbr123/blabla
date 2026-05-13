"""Tests for GET /metrics — Prometheus exposition endpoint."""
from __future__ import annotations

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
    content_type = r.headers["content-type"]
    assert "text/plain" in content_type
    # prometheus_client >=0.20 emits version=1.0.0; older emits version=0.0.4.
    # Both are valid Prometheus text exposition formats.
    assert "version=" in content_type
    assert "charset=utf-8" in content_type
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
