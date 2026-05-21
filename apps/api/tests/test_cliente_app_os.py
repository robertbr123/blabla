"""E2E /cliente-app/os."""
from __future__ import annotations

import collections.abc
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession

TEST_CPF = "11144477735"


@pytest_asyncio.fixture
async def existing_cliente(db_session: AsyncSession) -> ClienteAppUser:
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


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth(u: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(u.id)}"}


@pytest.mark.asyncio
async def test_criar_listar_os(client: AsyncClient, existing_cliente: ClienteAppUser) -> None:
    r = await client.post(
        "/api/v1/cliente-app/os",
        headers=_auth(existing_cliente),
        json={
            "tipo": "sem_internet",
            "descricao": "Internet caiu desde ontem a noite",
            "payload": {"desde_quando": "2026-05-20T22:00:00Z"},
        },
    )
    assert r.status_code == 201, r.text
    os_id = r.json()["id"]
    assert r.json()["status"] == "aberto"

    r = await client.get("/api/v1/cliente-app/os", headers=_auth(existing_cliente))
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == os_id

    r = await client.get(f"/api/v1/cliente-app/os/{os_id}", headers=_auth(existing_cliente))
    assert r.status_code == 200
    assert r.json()["tipo"] == "sem_internet"


@pytest.mark.asyncio
async def test_tipo_invalido_rejeita(client: AsyncClient, existing_cliente: ClienteAppUser) -> None:
    r = await client.post(
        "/api/v1/cliente-app/os",
        headers=_auth(existing_cliente),
        json={"tipo": "cancelamento", "descricao": "quero cancelar", "payload": {}},
    )
    assert r.status_code == 422  # cancelamento nao e suportado pelo app


@pytest.mark.asyncio
async def test_os_de_outro_cliente_invisivel(
    client: AsyncClient, existing_cliente: ClienteAppUser, db_session: AsyncSession
) -> None:
    # Cria OS pra outro user
    outro = ClienteAppUser(
        cpf_hash=hash_pii("52998224725"),
        cpf_last4="4725",
        cpf_encrypted=encrypt_pii("52998224725"),
        nome_encrypted=encrypt_pii("Outro"),
        telefone_encrypted=encrypt_pii("92999998888"),
        password_hash=hash_password("OutraSenha123!"),
        status="active",
    )
    db_session.add(outro)
    await db_session.commit()

    r = await client.post(
        "/api/v1/cliente-app/os",
        headers=_auth(outro),
        json={"tipo": "troca_plano", "descricao": "quero upgrade", "payload": {}},
    )
    assert r.status_code == 201
    outro_os_id = r.json()["id"]

    # existing_cliente nao deve ver
    r = await client.get(
        f"/api/v1/cliente-app/os/{outro_os_id}", headers=_auth(existing_cliente)
    )
    assert r.status_code == 404

    r = await client.get("/api/v1/cliente-app/os", headers=_auth(existing_cliente))
    assert r.json()["items"] == []
