"""Testes de integração para GET /api/v1/os/{id}/pdf e POST /enviar-pdf-tecnico."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import OrdemServico, OsStatus
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("EVOLUTION_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_KEY", "fake-key")


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


async def _seed_os(db_session: AsyncSession) -> OrdemServico:
    os_ = OrdemServico(
        codigo=f"OS-{uuid4().hex[:6]}",
        problema="Internet caindo",
        endereco="Rua das Flores, 123",
        status=OsStatus.CONCLUIDA,
        criada_em=datetime(2026, 5, 14, 8, 0, tzinfo=UTC),
        concluida_em=datetime(2026, 5, 14, 10, 30, tzinfo=UTC),
        csat=5,
        comentario_cliente="Ótimo atendimento",
    )
    db_session.add(os_)
    await db_session.flush()
    return os_


@pytest.mark.asyncio
async def test_pdf_requires_auth(client: AsyncClient, db_session: AsyncSession) -> None:
    os_ = await _seed_os(db_session)
    r = await client.get(f"/api/v1/os/{os_.id}/pdf")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_pdf_returns_pdf_bytes(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    os_ = await _seed_os(db_session)
    token = await _admin_token(client, created_user)
    r = await client.get(
        f"/api/v1/os/{os_.id}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"  # PDF magic bytes


@pytest.mark.asyncio
async def test_pdf_not_found(client: AsyncClient, created_user: dict[str, Any]) -> None:
    token = await _admin_token(client, created_user)
    r = await client.get(
        f"/api/v1/os/{uuid4()}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_enviar_pdf_sem_tecnico_retorna_422(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    os_ = await _seed_os(db_session)  # sem tecnico_id
    token = await _admin_token(client, created_user)
    r = await client.post(
        f"/api/v1/os/{os_.id}/enviar-pdf-tecnico",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_enviar_pdf_ao_tecnico(
    client: AsyncClient, created_user: dict[str, Any], db_session: AsyncSession
) -> None:
    from ondeline_api.db.models.business import Tecnico

    tecnico = Tecnico(nome="João Técnico", whatsapp="5511999990000", ativo=True)
    db_session.add(tecnico)
    await db_session.flush()

    os_ = await _seed_os(db_session)
    os_.tecnico_id = tecnico.id
    await db_session.flush()

    token = await _admin_token(client, created_user)
    with patch(
        "ondeline_api.api.v1.ordens_servico._send_whatsapp_document",
        new=AsyncMock(return_value=None),
    ):
        r = await client.post(
            f"/api/v1/os/{os_.id}/enviar-pdf-tecnico",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    assert r.json()["enviado"] is True
