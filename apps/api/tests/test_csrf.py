"""Tests for CSRF double-submit middleware."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.csrf import CSRFMiddleware


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CSRFMiddleware,
        exempt_paths=["/auth/login", "/auth/refresh", "/webhook"],
    )

    @app.get("/safe")
    async def safe() -> dict[str, str]:
        return {"ok": "yes"}

    @app.post("/state-change")
    async def state_change() -> dict[str, str]:
        return {"ok": "yes"}

    return app


@pytest.mark.asyncio
async def test_get_passes_without_csrf() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/safe")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_post_without_csrf_blocked() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_post_with_matching_csrf_passes() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change", headers={"X-CSRF": "abc"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_post_with_mismatched_csrf_blocked() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "abc")
        r = await c.post("/state-change", headers={"X-CSRF": "xyz"})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_exempt_path_skipped() -> None:
    app = make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/auth/login", json={})
        # 404 (rota inexistente em make_app) mas nao 403 do CSRF
        assert r.status_code != 403
