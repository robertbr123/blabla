"""Testes de integração para GET /api/v1/metricas/tecnicos."""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import OrdemServico, OsStatus, Tecnico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app


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


async def _seed_tecnico_com_os(
    db_session: AsyncSession,
    nome: str,
    os_count: int,
    csat: int | None = None,
    mes: datetime | None = None,
) -> Tecnico:
    """Cria um técnico e N OS concluídas no banco."""
    tecnico = Tecnico(nome=nome, ativo=True)
    db_session.add(tecnico)
    await db_session.flush()

    concluida = mes or datetime(2026, 5, 15, tzinfo=UTC)
    for _ in range(os_count):
        os_ = OrdemServico(
            codigo=f"OS-{uuid4().hex[:6]}",
            problema="Teste",
            endereco="Rua X, 1",
            status=OsStatus.CONCLUIDA,
            tecnico_id=tecnico.id,
            criada_em=datetime(2026, 5, 15, 8, 0, tzinfo=UTC),
            concluida_em=concluida,
            csat=csat,
        )
        db_session.add(os_)
    await db_session.flush()
    return tecnico


@pytest.mark.asyncio
async def test_ranking_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/metricas/tecnicos")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ranking_returns_list(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "Carlos", os_count=5, csat=5)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    tecnico = next((t for t in data if t["nome"] == "Carlos"), None)
    assert tecnico is not None
    assert tecnico["os_concluidas"] == 5
    assert tecnico["csat_avg"] == 5.0


@pytest.mark.asyncio
async def test_ranking_ordered_by_os_desc(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "Ana", os_count=3)
    await _seed_tecnico_com_os(db_session, "Pedro", os_count=7)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    os_counts = [t["os_concluidas"] for t in data if t["nome"] in ("Ana", "Pedro")]
    assert os_counts == sorted(os_counts, reverse=True)


@pytest.mark.asyncio
async def test_ranking_default_mes_current_month(
    client: AsyncClient, created_user: dict[str, Any]
) -> None:
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ranking_export_csv(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    await _seed_tecnico_com_os(db_session, "ExportTec", os_count=2)
    token = await _admin_token(client, created_user)
    r = await client.get(
        "/api/v1/metricas/tecnicos/export?mes=2026-05",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    lines = r.text.strip().split("\n")
    assert lines[0].startswith("Tecnico,")  # header
    assert any("ExportTec" in line for line in lines[1:])
