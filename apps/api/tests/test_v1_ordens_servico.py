"""Integration tests for /api/v1/os endpoints."""
from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Cliente, OrdemServico, OsStatus
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:  # type: ignore[type-arg]
    app = create_app()

    async def _override_db() -> Any:
        yield db_session

    async def _override_redis() -> Any:
        return redis_client

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    return app


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(db_session: AsyncSession) -> dict[str, Any]:
    email = f"admin-{uuid4().hex[:8]}@example.com"
    password = "Pa$$word123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        name="Test Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return {"email": email, "password": password, "id": user.id, "user": user}


async def _make_cliente(db_session: AsyncSession) -> Cliente:
    """Create a minimal Cliente row for FK satisfaction."""
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("000.000.000-00"),
        cpf_hash="test-cpf-hash-" + uuid4().hex[:8],
        nome_encrypted=encrypt_pii("Test Cliente"),
        whatsapp="5511900000000",
    )
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_tecnico(db_session: AsyncSession) -> Any:
    """Create a minimal Tecnico row (ativo=True, no whatsapp by default)."""
    from ondeline_api.db.models.business import Tecnico
    t = Tecnico(nome=f"Tec-{uuid4().hex[:6]}", ativo=True)
    db_session.add(t)
    await db_session.flush()
    return t


async def _make_os(
    db_session: AsyncSession,
    cliente: Cliente,
    tecnico: Any | None = None,
    *,
    codigo: str | None = None,
) -> OrdemServico:
    """Create a minimal OrdemServico row."""
    os_ = OrdemServico(
        codigo=codigo or f"OS-20260101-{uuid4().hex[:3]}",
        cliente_id=cliente.id,
        tecnico_id=tecnico.id if tecnico is not None else None,
        problema="Internet caindo frequentemente",
        endereco="Rua Teste, 123",
        status=OsStatus.PENDENTE,
    )
    db_session.add(os_)
    await db_session.flush()
    return os_


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_token(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    admin = await _make_admin(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        yield c, token, admin, db_session


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_os_returns_201_with_codigo(app_and_token: Any) -> None:
    """POST /api/v1/os creates an OS with a formatted codigo."""
    from unittest.mock import AsyncMock, patch

    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    tec = await _make_tecnico(db_session)

    with patch(
        "ondeline_api.api.v1.ordens_servico._send_whatsapp",
        new_callable=AsyncMock,
    ):
        r = await client.post(
            "/api/v1/os",
            json={
                "cliente_id": str(cliente.id),
                "tecnico_id": str(tec.id),
                "problema": "Sem sinal de internet",
                "endereco": "Av. Principal, 500",
            },
            headers=_auth(token),
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "codigo" in body
    # Codigo format: OS-YYYYMMDD-NNN
    assert body["codigo"].startswith("OS-")
    assert body["status"] == "pendente"
    assert body["problema"] == "Sem sinal de internet"
    assert body["tecnico_id"] == str(tec.id)


@pytest.mark.asyncio
async def test_list_os_returns_paginated(app_and_token: Any) -> None:
    """GET /api/v1/os returns paginated list."""
    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    await _make_os(db_session, cliente)
    await _make_os(db_session, cliente)

    r = await client.get("/api/v1/os?limit=1", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert len(body["items"]) == 1
    assert "next_cursor" in body


@pytest.mark.asyncio
async def test_get_os_returns_detail(app_and_token: Any) -> None:
    """GET /api/v1/os/{id} returns the OS detail."""
    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente)

    r = await client.get(f"/api/v1/os/{os_.id}", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(os_.id)
    assert body["codigo"] == os_.codigo


@pytest.mark.asyncio
async def test_get_os_404(app_and_token: Any) -> None:
    """GET /api/v1/os/{id} returns 404 for unknown id."""
    client, token, _admin, _db = app_and_token
    r = await client.get(f"/api/v1/os/{uuid4()}", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_os_updates_status(app_and_token: Any) -> None:
    """PATCH /api/v1/os/{id} updates status field."""
    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente)

    r = await client.patch(
        f"/api/v1/os/{os_.id}",
        json={"status": "em_andamento"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "em_andamento"

    await db_session.refresh(os_)
    assert os_.status == OsStatus.EM_ANDAMENTO


@pytest.mark.asyncio
async def test_upload_foto_appends_to_fotos(app_and_token: Any) -> None:
    """POST /api/v1/os/{id}/foto saves photo and appends metadata."""
    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente)

    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    r = await client.post(
        f"/api/v1/os/{os_.id}/foto",
        files={"file": ("foto.png", fake_image, "image/png")},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fotos"] is not None
    assert len(body["fotos"]) == 1
    assert body["fotos"][0]["mime"] == "image/png"

    await db_session.refresh(os_)
    assert os_.fotos is not None
    assert len(os_.fotos) == 1


@pytest.mark.asyncio
async def test_concluir_sets_status_and_csat(app_and_token: Any) -> None:
    """POST /api/v1/os/{id}/concluir sets status=concluida, concluida_em, csat."""
    client, token, _admin, db_session = app_and_token
    cliente = await _make_cliente(db_session)
    os_ = await _make_os(db_session, cliente)

    r = await client.post(
        f"/api/v1/os/{os_.id}/concluir",
        json={"csat": 5, "comentario": "Excelente atendimento!"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "concluida"
    assert body["csat"] == 5
    assert body["comentario_cliente"] == "Excelente atendimento!"
    assert body["concluida_em"] is not None

    await db_session.refresh(os_)
    assert os_.status == OsStatus.CONCLUIDA
    assert os_.csat == 5


@pytest.mark.asyncio
async def test_list_os_no_auth_returns_401(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    """GET /api/v1/os without auth returns 401."""
    app = _make_app(db_session, redis_client)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/os")
    assert r.status_code == 401


# ─── Repository-level tests ──────────────────────────────────────────────────


async def _make_cliente_repo(session: AsyncSession) -> Cliente:
    from ondeline_api.db.crypto import hash_pii
    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Joao"),
        whatsapp="5511111@s",
    )
    session.add(c)
    await session.flush()
    return c


async def _make_tecnico_repo(session: AsyncSession) -> "Any":
    from ondeline_api.db.models.business import Tecnico
    t = Tecnico(nome=f"Tec-{uuid4().hex[:6]}", ativo=True)
    session.add(t)
    await session.flush()
    return t


async def _make_os_repo(
    session: AsyncSession,
    cliente: Cliente,
    tecnico: "Any",
) -> OrdemServico:
    from ondeline_api.domain.os_sequence import next_codigo
    from ondeline_api.repositories.ordem_servico import OrdemServicoRepo as _Repo
    codigo = await next_codigo(session)
    repo = _Repo(session)
    return await repo.create(
        codigo=codigo,
        cliente_id=cliente.id,
        tecnico_id=tecnico.id,
        problema="sem internet",
        endereco="Rua A, 10",
    )


@pytest.mark.asyncio
async def test_list_paginated_by_cliente_id(db_session: AsyncSession) -> None:
    """list_paginated with cliente_id filter only returns OS for that client."""
    from ondeline_api.repositories.ordem_servico import OrdemServicoRepo as _Repo

    cliente = await _make_cliente_repo(db_session)
    tec = await _make_tecnico_repo(db_session)
    os1 = await _make_os_repo(db_session, cliente, tec)

    outros_cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("99988877766"),
        cpf_hash="other-hash-" + uuid4().hex[:8],
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5599999@s",
    )
    db_session.add(outros_cliente)
    await db_session.flush()
    tec2 = await _make_tecnico_repo(db_session)
    from ondeline_api.domain.os_sequence import next_codigo
    codigo2 = await next_codigo(db_session)
    await _Repo(db_session).create(
        codigo=codigo2, cliente_id=outros_cliente.id, tecnico_id=tec2.id,
        problema="outro", endereco="Rua B"
    )

    repo = _Repo(db_session)
    rows, _ = await repo.list_paginated(cliente_id=cliente.id)
    assert len(rows) == 1
    assert rows[0].id == os1.id


# ─── Reatribuir / Delete / Create-with-tecnico tests ────────────────────────


@pytest.mark.asyncio
async def test_reatribuir_troca_tecnico(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec1 = await _make_tecnico(db_session)
    tec1.whatsapp = "5511111@s"
    tec2 = await _make_tecnico(db_session)
    tec2.whatsapp = "5522222@s"
    await db_session.flush()
    os_ = await _make_os(db_session, cliente, tec1)
    admin = await _make_admin(db_session)

    app = _make_app(db_session, redis_client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch(
            "ondeline_api.api.v1.ordens_servico._send_whatsapp",
            new_callable=AsyncMock,
        ):
            r = await c.post(
                f"/api/v1/os/{os_.id}/reatribuir",
                json={"tecnico_id": str(tec2.id)},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tecnico_id"] == str(tec2.id)
    assert data["reatribuido_por"] == str(admin["user"].id)
    assert len(data["historico_reatribuicoes"]) == 1
    assert data["historico_reatribuicoes"][0]["de"] == str(tec1.id)


@pytest.mark.asyncio
async def test_reatribuir_concluida_retorna_422(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec1 = await _make_tecnico(db_session)
    tec2 = await _make_tecnico(db_session)
    os_ = await _make_os(db_session, cliente, tec1)
    os_.status = OsStatus.CONCLUIDA
    await db_session.flush()
    admin = await _make_admin(db_session)

    app = _make_app(db_session, redis_client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch(
            "ondeline_api.api.v1.ordens_servico._send_whatsapp",
            new_callable=AsyncMock,
        ):
            r = await c.post(
                f"/api/v1/os/{os_.id}/reatribuir",
                json={"tecnico_id": str(tec2.id)},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_os(
    db_session: AsyncSession, redis_client: Redis  # type: ignore[type-arg]
) -> None:
    from unittest.mock import AsyncMock, patch

    cliente = await _make_cliente(db_session)
    tec = await _make_tecnico(db_session)
    tec.whatsapp = "5533333@s"
    await db_session.flush()
    os_ = await _make_os(db_session, cliente, tec)
    admin = await _make_admin(db_session)

    app = _make_app(db_session, redis_client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _login(c, admin["email"], admin["password"])
        with patch(
            "ondeline_api.api.v1.ordens_servico._send_whatsapp",
            new_callable=AsyncMock,
        ):
            r = await c.delete(
                f"/api/v1/os/{os_.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
    assert r.status_code == 200
    assert r.json()["notif_tecnico"] is True
