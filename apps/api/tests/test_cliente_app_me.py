"""E2E /cliente-app/me + plano + avisos + PATCH/me + change-password."""
from __future__ import annotations

import collections.abc
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
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
def fake_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="12345",
        nome="Cliente Teste",
        cpf_cnpj=TEST_CPF,
        whatsapp="92981234567",
        contratos=[
            Contrato(id="c1", plano="Fibra 600", status="ativo", cidade="Manaus"),
        ],
        endereco=EnderecoSgp(cidade="Manaus", uf="AM"),
        titulos=[
            Fatura(
                id="t1",
                valor=129.90,
                vencimento="2026-06-10",
                status="aberto",
                link_pdf="https://sgp.exemplo/boleto/t1.pdf",
                codigo_pix="00020126...pix-t1",
            ),
            Fatura(
                id="t2",
                valor=129.90,
                vencimento="2026-05-10",
                status="pago",
                link_pdf="https://sgp.exemplo/boleto/t2.pdf",
                codigo_pix=None,
            ),
        ],
    )


@pytest.fixture
def app(
    db_session: AsyncSession,
    fake_sgp: ClienteSgp,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    async def _fake_lookup(_s: AsyncSession, _cpf: str) -> ClienteSgp:
        return fake_sgp

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_auth._sgp_lookup_by_cpf", _fake_lookup
    )

    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth(user: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(user.id)}"}


@pytest.mark.asyncio
async def test_me_returns_data(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get("/api/v1/cliente-app/me", headers=_auth(existing_cliente))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cpf_last4"] == TEST_CPF[-4:]
    assert data["nome"] == "Cliente Teste"
    assert data["plano_nome"] == "Fibra 600"


@pytest.mark.asyncio
async def test_plano_returns_contratos(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get("/api/v1/cliente-app/plano", headers=_auth(existing_cliente))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["contratos"]) == 1
    assert data["contratos"][0]["plano"] == "Fibra 600"


@pytest.mark.asyncio
async def test_avisos_empty(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get("/api/v1/cliente-app/avisos", headers=_auth(existing_cliente))
    assert r.status_code == 200
    assert r.json() == {"items": []}


@pytest.mark.asyncio
async def test_patch_me_updates_phone(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.patch(
        "/api/v1/cliente-app/me",
        headers=_auth(existing_cliente),
        json={"telefone": "92987654321"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["telefone"] == "92987654321"


@pytest.mark.asyncio
async def test_change_password_flow(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.post(
        "/api/v1/cliente-app/me/password",
        headers=_auth(existing_cliente),
        json={"current_password": "errada1234", "new_password": "NovaSenha456!"},
    )
    assert r.status_code == 401

    r = await client.post(
        "/api/v1/cliente-app/me/password",
        headers=_auth(existing_cliente),
        json={"current_password": "SenhaForte123!", "new_password": "NovaSenha456!"},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_faturas_lista_todas(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get(
        "/api/v1/cliente-app/faturas", headers=_auth(existing_cliente)
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 2
    # Ordem decrescente por vencimento
    assert items[0]["id"] == "t1"
    assert items[0]["tem_pix"] is True
    assert items[1]["tem_pix"] is False


@pytest.mark.asyncio
async def test_faturas_filtro_abertas(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get(
        "/api/v1/cliente-app/faturas?status=abertas",
        headers=_auth(existing_cliente),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "aberto"


@pytest.mark.asyncio
async def test_pix_da_fatura_aberta(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get(
        "/api/v1/cliente-app/faturas/t1/pix", headers=_auth(existing_cliente)
    )
    assert r.status_code == 200
    assert r.json()["codigo"].startswith("000201")


@pytest.mark.asyncio
async def test_pix_inexistente_retorna_404(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get(
        "/api/v1/cliente-app/faturas/t2/pix", headers=_auth(existing_cliente)
    )
    assert r.status_code == 404  # t2 nao tem codigo_pix
    r = await client.get(
        "/api/v1/cliente-app/faturas/inexistente/pix",
        headers=_auth(existing_cliente),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_boleto_url(
    client: AsyncClient, existing_cliente: ClienteAppUser
) -> None:
    r = await client.get(
        "/api/v1/cliente-app/faturas/t1/boleto", headers=_auth(existing_cliente)
    )
    assert r.status_code == 200
    assert r.json()["url"].endswith(".pdf")


@pytest.mark.asyncio
async def test_me_rejects_staff_token(client: AsyncClient) -> None:
    from uuid import uuid4

    staff_token = jwt_mod.encode_access_token(uuid4(), role="admin")
    r = await client.get(
        "/api/v1/cliente-app/me",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert r.status_code == 401
