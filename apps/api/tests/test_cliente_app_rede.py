"""E2E /api/v1/cliente-app/rede/* (app do cliente).

Reusa o get_rede_service fake (igual test_v1_rede), mas autentica como
ClienteAppUser e roda o cooldown contra a sessao real.
"""
from __future__ import annotations

import collections.abc
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    ResultadoTroca,
    StatusRede,
)
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

TEST_CPF = "11144477735"


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

    async def status_rede(self, cpf: str, serial: str | None = None) -> StatusRede:
        assert self._status is not None
        return self._status

    async def trocar_senha_wifi(
        self, *, cpf: str, nova_senha: str, serial: str | None, ator_user_id: UUID
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
        redes=[
            RedeWlan(instancia=1, ssid="CASA", enabled=True),
            RedeWlan(instancia=6, ssid="CASA", enabled=True),  # 2.4 + 5G mesmo SSID
        ],
    )


def _make_app(db_session: AsyncSession, fake: _FakeService) -> FastAPI:
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_rede_service() -> collections.abc.AsyncIterator[_FakeService]:
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_rede_service] = _override_rede_service
    return app


async def _make_cliente(db_session: AsyncSession) -> ClienteAppUser:
    u = ClienteAppUser(
        cpf_hash=hash_pii(TEST_CPF),
        cpf_last4=TEST_CPF[-4:],
        cpf_encrypted=encrypt_pii(TEST_CPF),
        nome_encrypted=encrypt_pii("Cliente Teste"),
        telefone_encrypted=encrypt_pii("92981234567"),
        password_hash=hash_password("SenhaForte123!"),
        sgp_id="12345",
        status="active",
    )
    db_session.add(u)
    await db_session.commit()
    return u


def _auth(u: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(u.id)}"}


async def test_status_encontrada(db_session: AsyncSession) -> None:
    fake = _FakeService(status=StatusRede(encontrada=True, device=_dev()))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/status", headers=_auth(u))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encontrada"] is True
    assert body["modelo"] == "AX1800"
    assert body["online"] is True
    # SSID repetido (2.4 + 5G) vira 1 so na resposta do cliente.
    assert [x["ssid"] for x in body["redes"]] == ["CASA"]


async def test_status_nao_encontrada(db_session: AsyncSession) -> None:
    """encontrada=False vira o gatilho da tela 'em construcao'."""
    fake = _FakeService(status=StatusRede(encontrada=False, motivo="onu_nao_encontrada"))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/cliente-app/rede/status", headers=_auth(u))
    assert r.status_code == 200, r.text
    assert r.json()["encontrada"] is False


async def test_trocar_senha_ok(db_session: AsyncSession) -> None:
    fake = _FakeService(troca=ResultadoTroca(device_id="30E1F1-AX1800-X", reiniciando=True))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "enviado"
    assert body["reiniciando"] is True


async def test_trocar_sem_token_401(db_session: AsyncSession) -> None:
    fake = _FakeService(troca=ResultadoTroca(device_id="X", reiniciando=False))
    app = _make_app(db_session, fake)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/cliente-app/rede/wifi/senha", json={"senha": "senhaboa123"})
    assert r.status_code == 401, r.text


async def test_trocar_onu_nao_encontrada_404(db_session: AsyncSession) -> None:
    fake = _FakeService(raise_troca=OnuNaoEncontradaError("sem device"))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 404, r.text


async def test_cooldown_429(db_session: AsyncSession) -> None:
    """Troca recente do mesmo cpf_hash -> 429 com minutos_restantes."""
    fake = _FakeService(troca=ResultadoTroca(device_id="X", reiniciando=False))
    app = _make_app(db_session, fake)
    u = await _make_cliente(db_session)
    # Registra uma troca AGORA (default created_at = now()).
    db_session.add(
        RedeWifiPedido(
            cpf_hash=hash_pii(TEST_CPF),
            device_id="30E1F1-AX1800-X",
            ator_user_id=u.id,
            status="enviado",
            reiniciou=True,
        )
    )
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/cliente-app/rede/wifi/senha",
            json={"senha": "senhaboa123"},
            headers=_auth(u),
        )
    assert r.status_code == 429, r.text
    assert r.json()["detail"]["minutos_restantes"] >= 1
