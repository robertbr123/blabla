"""Endpoints /api/v1/rede/* (RBAC tecnico/admin)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    ResultadoTroca,
    StatusRede,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ─── Fake service ────────────────────────────────────────────────────────────


class _FakeService:
    def __init__(
        self,
        *,
        status: StatusRede | None = None,
        troca: ResultadoTroca | None = None,
        raise_troca: Exception | None = None,
    ) -> None:
        self._status = status
        self._troca = troca
        self._raise = raise_troca

    async def status_rede(
        self, cliente_id: UUID, serial: str | None = None
    ) -> StatusRede:
        assert self._status is not None
        return self._status

    async def trocar_senha_wifi(
        self,
        *,
        cliente_id: UUID,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
    ) -> ResultadoTroca:
        if self._raise:
            raise self._raise
        assert self._troca is not None
        return self._troca


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        fabricante="INTELBRAS",
        online=True,
        redes=[RedeWlan(instancia=1, ssid="CASA_5G", enabled=True)],
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_app_overrides(
    db_session: AsyncSession,
    redis_client: Any,
    fake: _FakeService,
) -> FastAPI:
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    async def _override_rede_service() -> AsyncIterator[_FakeService]:
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_rede_service] = _override_rede_service
    return app


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_tecnico_user(db_session: AsyncSession) -> dict[str, Any]:
    email = f"tec-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=Role.TECNICO,
        name="Test Tecnico",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"email": email, "password": password, "id": user.id, "user": user}


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Any = Redis.from_url(
        str(get_settings().redis_url), decode_responses=True
    )
    yield client
    await client.aclose()


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_rede_encontrada(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """GET /api/v1/rede/{id} retorna 200 com modelo quando ONU encontrada."""
    dev = _dev()
    fake = _FakeService(
        status=StatusRede(encontrada=True, device=dev, pppoe_login="cli123")
    )
    app = _make_app_overrides(db_session, redis_client, fake)
    tec = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, tec["email"], tec["password"])
        r = await c.get(f"/api/v1/rede/{uuid4()}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encontrada"] is True
    assert body["modelo"] == "AX1800"
    assert body["online"] is True
    assert len(body["redes"]) == 1
    assert body["redes"][0]["ssid"] == "CASA_5G"


@pytest.mark.asyncio
async def test_trocar_senha_ok(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """POST /api/v1/rede/{id}/wifi/senha retorna 200 com reiniciando=True."""
    fake = _FakeService(
        troca=ResultadoTroca(device_id="30E1F1-AX1800-X", reiniciando=True)
    )
    app = _make_app_overrides(db_session, redis_client, fake)
    tec = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, tec["email"], tec["password"])
        r = await c.post(
            f"/api/v1/rede/{uuid4()}/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(token),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "enviado"
    assert body["reiniciando"] is True


@pytest.mark.asyncio
async def test_trocar_senha_onu_nao_encontrada(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """POST /api/v1/rede/{id}/wifi/senha retorna 404 quando ONU nao achada."""
    fake = _FakeService(raise_troca=OnuNaoEncontradaError("sem device"))
    app = _make_app_overrides(db_session, redis_client, fake)
    tec = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, tec["email"], tec["password"])
        r = await c.post(
            f"/api/v1/rede/{uuid4()}/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(token),
        )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_status_rede_sem_token(
    db_session: AsyncSession, redis_client: Any
) -> None:
    """GET /api/v1/rede/{id} sem token retorna 401."""
    fake = _FakeService()
    app = _make_app_overrides(db_session, redis_client, fake)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(f"/api/v1/rede/{uuid4()}")
    assert r.status_code == 401, r.text
