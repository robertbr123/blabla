"""Integration test: /healthz response shape includes celery queues."""
from __future__ import annotations

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
