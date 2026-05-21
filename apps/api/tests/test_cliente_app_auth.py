"""E2E cliente-app: register, login e ISOLAMENTO de audience.

O teste de isolamento e a garantia critica da fase: token cliente NUNCA
pode acessar endpoints staff, e token staff NUNCA pode acessar
endpoints cliente.
"""
from __future__ import annotations

import collections.abc
import os
import re
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.sgp.base import ClienteSgp, EnderecoSgp, SgpProviderEnum
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")

# CPF de teste com DVs validos
TEST_CPF = "11144477735"


class FakeEvolution:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, jid: str, text: str) -> dict[str, Any]:
        self.sent.append((jid, text))
        return {"status": "ok"}

    async def aclose(self) -> None:
        return None


@pytest_asyncio.fixture
async def redis_client() -> collections.abc.AsyncIterator[Redis]:  # type: ignore[type-arg]
    client: Redis = Redis.from_url(REDIS_URL, decode_responses=True)  # type: ignore[type-arg]
    try:
        yield client
    finally:
        await client.aclose()  # type: ignore[attr-defined]


@pytest.fixture
def fake_evolution() -> FakeEvolution:
    return FakeEvolution()


@pytest.fixture
def fake_sgp_cliente() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="12345",
        nome="Cliente Teste",
        cpf_cnpj=TEST_CPF,
        whatsapp="92981234567",
        contratos=[],
        endereco=EnderecoSgp(),
    )


@pytest.fixture
def app(
    db_session: AsyncSession,
    redis_client: Redis,  # type: ignore[type-arg]
    fake_evolution: FakeEvolution,
    fake_sgp_cliente: ClienteSgp,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    # Patch ANTES de criar o app pra que o modulo veja a versao mockada
    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth._evolution",
        lambda: fake_evolution,
    )

    async def _fake_sgp(_session: AsyncSession, cpf: str) -> ClienteSgp | None:
        if cpf == TEST_CPF:
            return fake_sgp_cliente
        return None

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth._sgp_lookup_by_cpf",
        _fake_sgp,
    )

    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_full_register_and_login(
    client: AsyncClient,
    fake_evolution: FakeEvolution,
) -> None:
    # 1. register/start
    r = await client.post(
        "/api/v1/cliente-app/auth/register/start", json={"cpf": TEST_CPF}
    )
    assert r.status_code == 200, r.text
    assert "****" in r.json()["masked_phone"]
    assert len(fake_evolution.sent) == 1
    sent_text = fake_evolution.sent[0][1]
    m = re.search(r"\*(\d{6})\*", sent_text)
    assert m, f"codigo nao encontrado em: {sent_text}"
    code = m.group(1)

    # 2. register/verify
    r = await client.post(
        "/api/v1/cliente-app/auth/register/verify",
        json={"cpf": TEST_CPF, "code": code},
    )
    assert r.status_code == 200, r.text
    setup_token = r.json()["setup_token"]

    # 3. register/password
    r = await client.post(
        "/api/v1/cliente-app/auth/register/password",
        json={"setup_token": setup_token, "password": "SenhaForte123!"},
    )
    assert r.status_code == 200, r.text
    access1 = r.json()["access_token"]
    payload = jwt_mod.decode_cliente_access_token(access1)
    assert payload["kind"] == "cliente"

    # 4. login com a senha
    r = await client.post(
        "/api/v1/cliente-app/auth/login",
        json={"cpf": TEST_CPF, "password": "SenhaForte123!"},
    )
    assert r.status_code == 200, r.text
    access2 = r.json()["access_token"]
    assert jwt_mod.decode_cliente_access_token(access2)["kind"] == "cliente"

    # 5. login com senha errada
    r = await client.post(
        "/api/v1/cliente-app/auth/login",
        json={"cpf": TEST_CPF, "password": "errada123"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_register_start_unknown_cpf_returns_404(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/cliente-app/auth/register/start", json={"cpf": "12345678909"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_isolation_cliente_token_rejected_by_staff_endpoint(
    client: AsyncClient,
) -> None:
    """Token de cliente NUNCA pode acessar endpoint staff."""
    cliente_token = jwt_mod.encode_cliente_access_token(uuid4())
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {cliente_token}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_isolation_staff_token_rejected_at_decode_level() -> None:
    """Token de staff NUNCA decodifica como cliente.

    Quando a Fase 3 adicionar GET /cliente-app/me este teste vira request HTTP.
    """
    staff_token = jwt_mod.encode_access_token(uuid4(), role="admin")
    with pytest.raises(jwt_mod.InvalidTokenKind):
        jwt_mod.decode_cliente_access_token(staff_token)
