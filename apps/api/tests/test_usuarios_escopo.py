"""Gestao de usuarios (/api/v1/usuarios) + escopo de cidades do atendente."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.auth.scope import clean_cidades, normalize_cidade
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaStatus,
    OrdemServico,
    OsStatus,
)
from ondeline_api.db.models.identity import Role, User
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_v1_conversas import _auth, _login, _make_app, redis_client  # noqa: F401

pytestmark = pytest.mark.asyncio

_PWD = "Pa$$word123"


async def _user(
    db: AsyncSession, role: Role, cidades: list[str] | None = None
) -> User:
    u = User(
        email=f"{role.value}-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(_PWD),
        role=role,
        name=f"Test {role.value}",
        is_active=True,
        cidades=cidades,
    )
    db.add(u)
    await db.flush()
    return u


async def _cliente(db: AsyncSession, cidade: str | None) -> Cliente:
    cpf = uuid4().hex[:11]
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii(cpf),
        cpf_hash=hash_pii(cpf),
        nome_encrypted=encrypt_pii("Fulano"),
        whatsapp=f"55{uuid4().int % 10**11:011d}@s.whatsapp.net",
        cidade=cidade,
    )
    db.add(c)
    await db.flush()
    return c


async def _conversa(db: AsyncSession, cliente: Cliente | None) -> Conversa:
    c = Conversa(
        whatsapp=f"55{uuid4().int % 10**11:011d}",
        cliente_id=cliente.id if cliente else None,
        status=ConversaStatus.AGUARDANDO,
    )
    db.add(c)
    await db.flush()
    return c


async def _os(db: AsyncSession, cliente: Cliente | None) -> OrdemServico:
    o = OrdemServico(
        codigo=f"OS-T-{uuid4().hex[:8]}",
        cliente_id=cliente.id if cliente else None,
        problema="sem sinal",
        endereco="Rua X",
        status=OsStatus.PENDENTE,
    )
    db.add(o)
    await db.flush()
    return o


@pytest_asyncio.fixture
async def ctx(db_session: AsyncSession, redis_client: Any) -> Any:  # noqa: F811
    app = _make_app(db_session, redis_client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, db_session


async def _token(client: AsyncClient, user: User) -> dict[str, str]:
    return _auth(await _login(client, user.email, _PWD))


# ── normalizacao ────────────────────────────────────────────────────────────


async def test_normalize_e_clean_cidades() -> None:
    assert normalize_cidade("  Eirunepé ") == "eirunepe"
    assert normalize_cidade("IPIXUNA") == "ipixuna"
    assert clean_cidades([" Ipixuna", "ipixuna", "", "Eirunepé", "EIRUNEPE"]) == [
        "Ipixuna",
        "Eirunepé",
    ]


# ── escopo: conversas ───────────────────────────────────────────────────────


async def test_atendente_so_ve_conversas_das_suas_cidades(ctx: Any) -> None:
    client, db = ctx
    at = await _user(db, Role.ATENDENTE, ["Ipixuna"])
    dentro = await _conversa(db, await _cliente(db, "IPIXUNA "))  # caixa/espaco diferentes
    fora = await _conversa(db, await _cliente(db, "Itamarati"))
    sem_cliente = await _conversa(db, None)
    sem_cidade = await _conversa(db, await _cliente(db, None))
    h = await _token(client, at)

    r = await client.get("/api/v1/conversas?limit=200", headers=h)
    assert r.status_code == 200, r.text
    ids = {i["id"] for i in r.json()["items"]}
    assert str(dentro.id) in ids
    assert str(sem_cliente.id) in ids  # contato novo aparece pra todos
    assert str(sem_cidade.id) in ids
    assert str(fora.id) not in ids

    assert (await client.get(f"/api/v1/conversas/{dentro.id}", headers=h)).status_code == 200
    # Fora do escopo responde igual a inexistente — em leitura e em escrita.
    assert (await client.get(f"/api/v1/conversas/{fora.id}", headers=h)).status_code == 404
    assert (await client.get(f"/api/v1/conversas/{fora.id}/mensagens", headers=h)).status_code == 404
    r = await client.post(
        f"/api/v1/conversas/{fora.id}/responder", json={"text": "oi"}, headers=h
    )
    assert r.status_code == 404
    r = await client.post(f"/api/v1/conversas/{fora.id}/stream-ticket", headers=h)
    assert r.status_code == 404


async def test_cidade_com_acento_casa_sem_acento(ctx: Any) -> None:
    client, db = ctx
    at = await _user(db, Role.ATENDENTE, ["Eirunepe"])
    conv = await _conversa(db, await _cliente(db, "Eirunepé"))
    h = await _token(client, at)
    assert (await client.get(f"/api/v1/conversas/{conv.id}", headers=h)).status_code == 200


async def test_atendente_sem_cidades_e_admin_veem_tudo(ctx: Any) -> None:
    client, db = ctx
    conv = await _conversa(db, await _cliente(db, "Itamarati"))
    for user in (
        await _user(db, Role.ATENDENTE, None),
        await _user(db, Role.ATENDENTE, []),
        await _user(db, Role.ADMIN, None),
    ):
        h = await _token(client, user)
        assert (await client.get(f"/api/v1/conversas/{conv.id}", headers=h)).status_code == 200


# ── escopo: OS e metricas ───────────────────────────────────────────────────


async def test_atendente_so_ve_os_das_suas_cidades(ctx: Any) -> None:
    client, db = ctx
    at = await _user(db, Role.ATENDENTE, ["Ipixuna"])
    dentro = await _os(db, await _cliente(db, "Ipixuna"))
    fora = await _os(db, await _cliente(db, "Itamarati"))
    h = await _token(client, at)

    r = await client.get("/api/v1/os?limit=200", headers=h)
    assert r.status_code == 200, r.text
    ids = {i["id"] for i in r.json()["items"]}
    assert str(dentro.id) in ids
    assert str(fora.id) not in ids
    assert (await client.get(f"/api/v1/os/{dentro.id}", headers=h)).status_code == 200
    assert (await client.get(f"/api/v1/os/{fora.id}", headers=h)).status_code == 404
    r = await client.patch(f"/api/v1/os/{fora.id}", json={"status": "cancelada"}, headers=h)
    assert r.status_code == 404


async def test_metricas_contam_so_o_escopo(ctx: Any) -> None:
    client, db = ctx
    admin = await _user(db, Role.ADMIN)
    at = await _user(db, Role.ATENDENTE, [f"Cidade-{uuid4().hex[:6]}"])  # nenhuma conversa nela
    await _conversa(db, await _cliente(db, "Itamarati"))
    await _os(db, await _cliente(db, "Itamarati"))

    total = (await client.get("/api/v1/metricas", headers=await _token(client, admin))).json()
    meu = (await client.get("/api/v1/metricas", headers=await _token(client, at))).json()
    assert meu["conversas_aguardando"] < total["conversas_aguardando"]
    assert meu["os_abertas"] < total["os_abertas"]


# ── CRUD de usuarios ────────────────────────────────────────────────────────


async def test_admin_cria_atendente_com_cidades_e_ele_loga(ctx: Any) -> None:
    client, db = ctx
    h = await _token(client, await _user(db, Role.ADMIN))
    email = f"novo-{uuid4().hex[:8]}@Example.com"
    r = await client.post(
        "/api/v1/usuarios",
        json={
            "email": email,
            "name": "Novo Atendente",
            "role": "atendente",
            "password": "Senha#Forte9",
            "cidades": ["Ipixuna", "ipixuna", " Eirunepé "],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email.lower()
    assert body["cidades"] == ["Ipixuna", "Eirunepé"]
    assert "password" not in body and "password_hash" not in body

    # email duplicado (mesmo com outra caixa)
    r2 = await client.post(
        "/api/v1/usuarios",
        json={"email": email.upper(), "name": "X", "role": "atendente", "password": "Senha#Forte9"},
        headers=h,
    )
    assert r2.status_code == 409

    tok = await _login(client, email.lower(), "Senha#Forte9")
    me = (await client.get("/auth/me", headers=_auth(tok))).json()
    assert me["role"] == "atendente"
    assert me["cidades"] == ["Ipixuna", "Eirunepé"]

    lista = (await client.get("/api/v1/usuarios", headers=h)).json()
    assert any(u["id"] == body["id"] for u in lista)


async def test_so_admin_gerencia_usuarios(ctx: Any) -> None:
    client, db = ctx
    h = await _token(client, await _user(db, Role.ATENDENTE))
    assert (await client.get("/api/v1/usuarios", headers=h)).status_code == 403
    assert (await client.get("/api/v1/usuarios/cidades", headers=h)).status_code == 403
    r = await client.post(
        "/api/v1/usuarios",
        json={"email": "x@example.com", "name": "X", "role": "admin", "password": "Senha#Forte9"},
        headers=h,
    )
    assert r.status_code == 403


async def test_desativar_e_trocar_senha(ctx: Any) -> None:
    client, db = ctx
    h = await _token(client, await _user(db, Role.ADMIN))
    alvo = await _user(db, Role.ATENDENTE, ["Ipixuna"])
    alvo_h = await _token(client, alvo)

    r = await client.patch(
        f"/api/v1/usuarios/{alvo.id}", json={"password": "Outra#Senha77"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert (await client.post("/auth/login", json={"email": alvo.email, "password": _PWD})).status_code == 401
    await _login(client, alvo.email, "Outra#Senha77")

    r = await client.patch(f"/api/v1/usuarios/{alvo.id}", json={"is_active": False}, headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    # token antigo para de valer na hora
    assert (await client.get("/api/v1/conversas", headers=alvo_h)).status_code == 401

    # virar admin limpa o escopo
    r = await client.patch(
        f"/api/v1/usuarios/{alvo.id}", json={"is_active": True, "role": "admin"}, headers=h
    )
    assert r.json()["role"] == "admin" and r.json()["cidades"] == []


async def test_admin_nao_se_tranca_pra_fora(ctx: Any) -> None:
    client, db = ctx
    eu = await _user(db, Role.ADMIN)
    h = await _token(client, eu)
    for patch in ({"is_active": False}, {"role": "atendente"}):
        r = await client.patch(f"/api/v1/usuarios/{eu.id}", json=patch, headers=h)
        assert r.status_code == 400, r.text


async def test_tecnico_nao_aparece_nem_e_editavel(ctx: Any) -> None:
    client, db = ctx
    h = await _token(client, await _user(db, Role.ADMIN))
    tec = await _user(db, Role.TECNICO)
    lista = (await client.get("/api/v1/usuarios", headers=h)).json()
    assert all(u["id"] != str(tec.id) for u in lista)
    r = await client.patch(f"/api/v1/usuarios/{tec.id}", json={"name": "X"}, headers=h)
    assert r.status_code == 404


async def test_lista_de_cidades_agrupa_grafias(ctx: Any) -> None:
    client, db = ctx
    h = await _token(client, await _user(db, Role.ADMIN))
    nome = f"Zeta{uuid4().hex[:6]}"
    await _cliente(db, nome)
    await _cliente(db, nome)
    await _cliente(db, nome.upper())
    cidades = (await client.get("/api/v1/usuarios/cidades", headers=h)).json()
    assert nome in cidades
    assert nome.upper() not in cidades
