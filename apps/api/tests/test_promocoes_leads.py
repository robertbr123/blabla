"""Testes dos endpoints de detalhe e interesse (leads) de promoções."""
from __future__ import annotations

import collections.abc
import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.identity import Role, User
from ondeline_api.db.models.promocoes import Promocao, PromocaoLead
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def cliente(db_session: AsyncSession) -> ClienteAppUser:
    u = ClienteAppUser(
        cpf_hash=hash_pii("11144477735"),
        cpf_last4="7735",
        cpf_encrypted=encrypt_pii("11144477735"),
        nome_encrypted=encrypt_pii("Cliente Teste"),
        telefone_encrypted=encrypt_pii("92981234567"),
        password_hash=hash_password("SenhaForte123!"),
        sgp_id="12345",
        status="active",
    )
    db_session.add(u)
    await db_session.commit()
    return u


@pytest_asyncio.fixture
async def promo_ativa(db_session: AsyncSession) -> Promocao:
    p = Promocao(
        titulo="Promo Teste",
        subtitulo="Subtítulo da promo",
        cta_action="info",
        tipo="generica",
        ativa=True,
        ordem=0,
        segmento="todos",
        descricao_longa="Descrição longa da promoção para testar.",
        regulamento="Válida apenas para testes.",
    )
    db_session.add(p)
    await db_session.commit()
    return p


@pytest_asyncio.fixture
async def promo_inativa(db_session: AsyncSession) -> Promocao:
    p = Promocao(
        titulo="Promo Inativa",
        subtitulo="",
        cta_action="info",
        tipo="generica",
        ativa=False,
        ordem=1,
        segmento="todos",
    )
    db_session.add(p)
    await db_session.commit()
    return p


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    instance = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    instance.dependency_overrides[get_db] = _override_db
    return instance


@pytest_asyncio.fixture
async def ac(app: FastAPI) -> collections.abc.AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth(user: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(user.id)}"}


# ── testes ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interesse_cria_lead(
    ac: AsyncClient,
    cliente: ClienteAppUser,
    promo_ativa: Promocao,
    db_session: AsyncSession,
) -> None:
    r = await ac.post(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}/interesse",
        headers=_auth(cliente),
        json={"contrato_id": "c1"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["ja_registrado"] is False

    lead = (
        await db_session.execute(
            select(PromocaoLead).where(
                PromocaoLead.promocao_id == promo_ativa.id,
                PromocaoLead.cliente_app_user_id == cliente.id,
            )
        )
    ).scalar_one()
    assert lead.nome_snapshot == "Cliente Teste"
    assert lead.status == "novo"


@pytest.mark.asyncio
async def test_interesse_idempotente(
    ac: AsyncClient,
    cliente: ClienteAppUser,
    promo_ativa: Promocao,
    db_session: AsyncSession,
) -> None:
    headers = _auth(cliente)
    r1 = await ac.post(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}/interesse",
        headers=headers,
        json={},
    )
    assert r1.status_code == 200
    assert r1.json()["ja_registrado"] is False

    r2 = await ac.post(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}/interesse",
        headers=headers,
        json={},
    )
    assert r2.status_code == 200
    assert r2.json()["ja_registrado"] is True

    count = (
        await db_session.scalar(
            select(func.count()).where(
                PromocaoLead.promocao_id == promo_ativa.id,
                PromocaoLead.cliente_app_user_id == cliente.id,
            )
        )
    ) or 0
    assert count == 1


@pytest.mark.asyncio
async def test_detalhe_retorna_campos_e_interesse(
    ac: AsyncClient,
    cliente: ClienteAppUser,
    promo_ativa: Promocao,
) -> None:
    headers = _auth(cliente)

    r = await ac.get(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["titulo"] == "Promo Teste"
    assert data["descricao_longa"] == "Descrição longa da promoção para testar."
    assert data["regulamento"] == "Válida apenas para testes."
    assert data["interesse_registrado"] is False

    # Depois de registrar o interesse, o campo deve vir True
    await ac.post(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}/interesse",
        headers=headers,
        json={},
    )
    r2 = await ac.get(
        f"/api/v1/cliente-app/promocoes/{promo_ativa.id}",
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["interesse_registrado"] is True


@pytest.mark.asyncio
async def test_detalhe_promo_inativa_404(
    ac: AsyncClient,
    cliente: ClienteAppUser,
    promo_inativa: Promocao,
) -> None:
    headers = _auth(cliente)

    r = await ac.get(
        f"/api/v1/cliente-app/promocoes/{promo_inativa.id}",
        headers=headers,
    )
    assert r.status_code == 404

    r2 = await ac.post(
        f"/api/v1/cliente-app/promocoes/{promo_inativa.id}/interesse",
        headers=headers,
        json={},
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_detalhe_promo_inexistente_404(
    ac: AsyncClient,
    cliente: ClienteAppUser,
) -> None:
    headers = _auth(cliente)
    fake_id = uuid.uuid4()

    r = await ac.get(
        f"/api/v1/cliente-app/promocoes/{fake_id}",
        headers=headers,
    )
    assert r.status_code == 404

    r2 = await ac.post(
        f"/api/v1/cliente-app/promocoes/{fake_id}/interesse",
        headers=headers,
        json={},
    )
    assert r2.status_code == 404


# ── helpers admin ──────────────────────────────────────────────────────────────


async def _make_admin(db_session: AsyncSession) -> User:
    u = User(
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("Admin123!"),
        role=Role.ADMIN,
        name="Admin Teste",
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


def _auth_admin(user: User) -> dict[str, str]:
    token = jwt_mod.encode_access_token(user.id, Role.ADMIN)
    return {"Authorization": f"Bearer {token}"}


# ── testes admin ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_lista_leads_com_filtro(
    ac: AsyncClient,
    promo_ativa: Promocao,
    db_session: AsyncSession,
) -> None:
    admin = await _make_admin(db_session)
    headers = _auth_admin(admin)

    # Cria 2 leads direto na DB com status diferentes.
    lead1 = PromocaoLead(
        promocao_id=promo_ativa.id,
        cliente_app_user_id=uuid.uuid4(),
        nome_snapshot="Lead Novo",
        telefone_snapshot="92911111111",
        status="novo",
    )
    lead2 = PromocaoLead(
        promocao_id=promo_ativa.id,
        cliente_app_user_id=uuid.uuid4(),
        nome_snapshot="Lead Contatado",
        telefone_snapshot="92922222222",
        status="contatado",
    )
    db_session.add_all([lead1, lead2])
    await db_session.commit()

    # Sem filtro → 2 leads com promocao_titulo
    r = await ac.get("/api/v1/admin/promocoes/leads", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 2
    assert all(item["promocao_titulo"] == "Promo Teste" for item in data)

    # Filtro por status → 1 lead
    r2 = await ac.get(
        "/api/v1/admin/promocoes/leads?status_filtro=novo", headers=headers
    )
    assert r2.status_code == 200, r2.text
    assert len(r2.json()) == 1
    assert r2.json()[0]["nome"] == "Lead Novo"


@pytest.mark.asyncio
async def test_admin_patch_lead_status(
    ac: AsyncClient,
    promo_ativa: Promocao,
    db_session: AsyncSession,
) -> None:
    admin = await _make_admin(db_session)
    headers = _auth_admin(admin)

    lead = PromocaoLead(
        promocao_id=promo_ativa.id,
        cliente_app_user_id=uuid.uuid4(),
        nome_snapshot="Lead Patch",
        telefone_snapshot="92933333333",
        status="novo",
    )
    db_session.add(lead)
    await db_session.commit()

    # PATCH status valido
    r = await ac.patch(
        f"/api/v1/admin/promocoes/leads/{lead.id}",
        headers=headers,
        json={"status": "contatado"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "contatado"

    # PATCH status invalido → 422
    r2 = await ac.patch(
        f"/api/v1/admin/promocoes/leads/{lead.id}",
        headers=headers,
        json={"status": "banana"},
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_admin_listar_inclui_leads_count(
    ac: AsyncClient,
    promo_ativa: Promocao,
    db_session: AsyncSession,
) -> None:
    admin = await _make_admin(db_session)
    headers = _auth_admin(admin)

    lead = PromocaoLead(
        promocao_id=promo_ativa.id,
        cliente_app_user_id=uuid.uuid4(),
        nome_snapshot="Lead Count",
        telefone_snapshot="92944444444",
        status="novo",
    )
    db_session.add(lead)
    await db_session.commit()

    r = await ac.get("/api/v1/admin/promocoes", headers=headers)
    assert r.status_code == 200, r.text
    promos = r.json()
    promo_data = next(p for p in promos if str(p["id"]) == str(promo_ativa.id))
    assert promo_data["leads_count"] == 1
