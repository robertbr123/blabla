"""Endpoints /api/v1/conversas/{id}/rede/* (rede na conversa, dashboard)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    DiagnosticoRede,
    ResultadoReboot,
    ResultadoTroca,
    StatusRede,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

CPF = "01882354265"


class _FakeService:
    def __init__(self) -> None:
        self.cpf_recebido: str | None = None

    async def status_rede(self, cpf: str, serial: str | None = None) -> StatusRede:
        self.cpf_recebido = cpf
        return StatusRede(encontrada=True, device=_dev())

    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None
    ) -> DiagnosticoRede:
        self.cpf_recebido = cpf
        return DiagnosticoRede(encontrada=True, device=_dev())

    async def trocar_senha_wifi(
        self, *, cpf: str, nova_senha: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoTroca:
        self.cpf_recebido = cpf
        return ResultadoTroca(device_id="DEV-X", reiniciando=True)

    async def reiniciar_onu(
        self, *, cpf: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoReboot:
        self.cpf_recebido = cpf
        return ResultadoReboot(device_id="DEV-X")


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(device_id="DEV-X", modelo="AX1800", online=True)


def _make_app(db_session: AsyncSession, redis_client: Any, fake: _FakeService) -> FastAPI:
    app = create_app()

    async def _db() -> Any:
        yield db_session

    async def _redis() -> Any:
        return redis_client

    async def _svc() -> AsyncIterator[_FakeService]:
        yield fake

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_rede_service] = _svc
    return app


async def _login(c: AsyncClient, email: str, password: str) -> str:
    r = await c.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(t: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {t}"}


async def _make_user(db_session: AsyncSession, role: Role) -> dict[str, Any]:
    email = f"u-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    u = User(email=email, password_hash=hash_password(password), role=role,
             name="T", is_active=True)
    db_session.add(u)
    await db_session.flush()
    return {"email": email, "password": password, "id": u.id}


async def _make_conversa(db_session: AsyncSession, *, com_cliente: bool) -> UUID:
    cliente_id = None
    if com_cliente:
        cli = Cliente(
            cpf_cnpj_encrypted=encrypt_pii(CPF),
            cpf_hash=hash_pii(CPF),
            nome_encrypted=encrypt_pii("Fulano"),
            whatsapp="559900000000",
        )
        db_session.add(cli)
        await db_session.flush()
        cliente_id = cli.id
    conv = Conversa(whatsapp="559900000000", cliente_id=cliente_id)
    db_session.add(conv)
    await db_session.flush()
    return conv.id


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Any = Redis.from_url(str(get_settings().redis_url), decode_responses=True)
    yield client
    await client.aclose()


async def test_diagnostico_da_conversa_resolve_cpf(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/diagnostico", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is True
    assert fake.cpf_recebido == CPF


async def test_status_da_conversa_atendente_ok(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/status", headers=_auth(token))
    assert r.status_code == 200, r.text


async def test_conversa_sem_cliente_vinculado_409(
    db_session: AsyncSession, redis_client: Any
) -> None:
    fake = _FakeService()
    app = _make_app(db_session, redis_client, fake)
    user = await _make_user(db_session, Role.ATENDENTE)
    conv_id = await _make_conversa(db_session, com_cliente=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user["email"], user["password"])
        r = await c.get(f"/api/v1/conversas/{conv_id}/rede/diagnostico", headers=_auth(token))
    assert r.status_code == 409, r.text
