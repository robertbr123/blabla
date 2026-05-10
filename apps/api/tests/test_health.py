"""Tests for /healthz and /livez endpoints."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from ondeline_api.deps import get_db, get_redis


@pytest.mark.asyncio
async def test_livez_returns_200(client: AsyncClient) -> None:
    response = await client.get("/livez")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_healthz_returns_200_when_all_ok(
    app: FastAPI, client: AsyncClient, healthy_deps: dict[str, Any]
) -> None:
    app.dependency_overrides[get_db] = lambda: healthy_deps["db"]
    app.dependency_overrides[get_redis] = lambda: healthy_deps["redis"]

    response = await client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_healthz_returns_503_when_db_down(
    app: FastAPI, client: AsyncClient, broken_db_deps: dict[str, Any]
) -> None:
    app.dependency_overrides[get_db] = lambda: broken_db_deps["db"]
    app.dependency_overrides[get_redis] = lambda: broken_db_deps["redis"]

    response = await client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"].startswith("error")
    assert body["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_healthz_503_when_db_dependency_yields_broken(
    app: FastAPI, client: AsyncClient, broken_db: Any, healthy_deps: dict[str, Any]
) -> None:
    """The dependency yields a stub whose `execute()` raises ConnectionError; the route handler catches it and returns 503."""

    async def yield_broken() -> AsyncIterator[Any]:
        yield broken_db

    app.dependency_overrides[get_db] = yield_broken
    app.dependency_overrides[get_redis] = lambda: healthy_deps["redis"]

    response = await client.get("/healthz")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"].startswith("error")
