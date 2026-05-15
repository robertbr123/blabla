"""Testes de integração para /api/v1/planos."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.config import get_settings
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:  # type: ignore[type-arg]
    r: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield r
    await r.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    application = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _redis() -> Any:
        return redis_client

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[get_redis] = _redis
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client: AsyncClient, created_user: dict[str, Any]) -> str:
    r = await client.post(
        "/auth/login",
        json={"email": created_user["email"], "password": created_user["password"]},
    )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


@pytest.mark.asyncio
async def test_list_planos_public(client: AsyncClient) -> None:
    r = await client.get("/api/v1/planos")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "nome" in first
    assert "preco" in first
    assert "index" in first
    assert "ativo" in first
    assert "destaque" in first


@pytest.mark.asyncio
async def test_create_plano_requires_auth(client: AsyncClient) -> None:
    body = {"nome": "Teste", "preco": 99.0, "velocidade": "100MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "nome": "Fibra Max",
        "preco": 199.0,
        "velocidade": "200MB",
        "extras": ["IP fixo"],
        "descricao": "Para empresas",
        "ativo": True,
        "destaque": False,
    }
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["nome"] == "Fibra Max"
    assert data["preco"] == 199.0
    assert isinstance(data["index"], int)

    r2 = await client.get("/api/v1/planos")
    names = [p["nome"] for p in r2.json()]
    assert "Fibra Max" in names


@pytest.mark.asyncio
async def test_update_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"nome": "Para Editar", "preco": 100.0, "velocidade": "50MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    idx = r.json()["index"]

    updated = {**body, "preco": 120.0, "destaque": True}
    r2 = await client.patch(f"/api/v1/planos/{idx}", json=updated, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["preco"] == 120.0
    assert r2.json()["destaque"] is True


@pytest.mark.asyncio
async def test_update_plano_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    body = {"nome": "X", "preco": 1.0, "velocidade": "1MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.patch("/api/v1/planos/9999", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_plano(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"nome": "Para Deletar", "preco": 50.0, "velocidade": "10MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.post("/api/v1/planos", json=body, headers=headers)
    idx = r.json()["index"]

    r2 = await client.delete(f"/api/v1/planos/{idx}", headers=headers)
    assert r2.status_code == 204

    r3 = await client.get("/api/v1/planos")
    names = [p["nome"] for p in r3.json()]
    assert "Para Deletar" not in names


@pytest.mark.asyncio
async def test_delete_plano_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    r = await client.delete("/api/v1/planos/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_plano_requires_auth(client: AsyncClient) -> None:
    body = {"nome": "X", "preco": 1.0, "velocidade": "1MB", "extras": [], "descricao": "", "ativo": True, "destaque": False}
    r = await client.patch("/api/v1/planos/0", json=body)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_plano_requires_auth(client: AsyncClient) -> None:
    r = await client.delete("/api/v1/planos/0")
    assert r.status_code == 401
