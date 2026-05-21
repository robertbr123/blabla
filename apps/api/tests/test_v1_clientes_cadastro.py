"""Integration tests for /api/v1/clientes-campo endpoints."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.auth.passwords import hash_password
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import ClienteCadastro, Tecnico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db, get_redis
from ondeline_api.main import create_app
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


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


async def _make_tecnico_user(
    db_session: AsyncSession,
) -> tuple[User, Tecnico, str]:
    pw = "test-pwd-123!"
    email = f"tec_cli_{uuid4().hex[:6]}@test.example"
    user = User(
        email=email,
        password_hash=hash_password(pw),
        role=Role.TECNICO,
        name="Tec Cliente",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    tec = Tecnico(nome="Tec Cliente", user_id=user.id, ativo=True)
    db_session.add(tec)
    await db_session.flush()
    return user, tec, pw


@pytest_asyncio.fixture
async def redis_client() -> Any:
    client: Redis = Redis.from_url(str(get_settings().redis_url), decode_responses=True)  # type: ignore[type-arg]
    yield client
    await client.aclose()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def app_and_tecnico(db_session: AsyncSession, redis_client: Redis) -> Any:  # type: ignore[type-arg]
    app = _make_app(db_session, redis_client)
    user, tec, pw = await _make_tecnico_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        token = await _login(c, user.email, pw)
        yield c, token, user, tec, db_session


async def _make_cliente_campo(
    db_session: AsyncSession,
    *,
    installer_user_id: Any,
    installer_nome: str,
) -> ClienteCadastro:
    from ondeline_api.db.crypto import encrypt_pii, hash_pii

    cpf = "12345678901"
    cliente = ClienteCadastro(
        cpf_hash=hash_pii(cpf),
        cpf_encrypted=encrypt_pii(cpf),
        nome_encrypted=encrypt_pii("Cliente Campo"),
        dob=date(1990, 1, 1),
        telefone_encrypted=encrypt_pii("5592999999999"),
        address="Rua Teste",
        number="100",
        city="Manaus",
        plan_nome="Plano 500MB",
        due_date=10,
        installer_user_id=installer_user_id,
        installer_nome=installer_nome,
        registration_date=date.today(),
    )
    db_session.add(cliente)
    await db_session.flush()
    return cliente


@pytest.mark.asyncio
async def test_tecnico_pode_enviar_foto_para_cliente_cadastrado(
    app_and_tecnico: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, token, user, _tec, db_session = app_and_tecnico
    cliente = await _make_cliente_campo(
        db_session,
        installer_user_id=user.id,
        installer_nome=user.name,
    )
    monkeypatch.setenv("CLIENTE_FOTOS_DIR", str(tmp_path / "cliente-fotos"))

    files = {"file": ("instalacao.jpg", b"\x89PNG\r\n\x1a\n", "image/png")}
    r = await client.post(
        f"/api/v1/clientes-campo/{cliente.id}/fotos",
        data={"tipo": "instalacao"},
        files=files,
        headers=_auth(token),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["fotos"], list)
    assert len(body["fotos"]) == 1
    assert body["fotos"][0]["mime"] == "image/png"
    assert body["fotos"][0]["tipo"] == "instalacao"
    saved = Path(body["fotos"][0]["url"])
    assert saved.exists()
    assert str(saved).startswith(str(tmp_path / "cliente-fotos"))


@pytest.mark.asyncio
async def test_upload_foto_aceita_octet_stream_quando_extensao_e_imagem(
    app_and_tecnico: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, token, user, _tec, db_session = app_and_tecnico
    cliente = await _make_cliente_campo(
        db_session,
        installer_user_id=user.id,
        installer_nome=user.name,
    )
    monkeypatch.setenv("CLIENTE_FOTOS_DIR", str(tmp_path / "cliente-fotos"))

    files = {"file": ("instalacao.heic", b"fake-heic-binary", "application/octet-stream")}
    r = await client.post(
        f"/api/v1/clientes-campo/{cliente.id}/fotos",
        data={"tipo": "instalacao"},
        files=files,
        headers=_auth(token),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["fotos"], list)
    assert len(body["fotos"]) == 1
    assert body["fotos"][0]["tipo"] == "instalacao"
    assert body["fotos"][0]["mime"] == "image/heic"


@pytest.mark.asyncio
async def test_tecnico_pode_enviar_foto_quando_cliente_tem_so_installer_nome(
    app_and_tecnico: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, token, user, _tec, db_session = app_and_tecnico
    cliente = await _make_cliente_campo(
        db_session,
        installer_user_id=None,
        installer_nome=user.name,
    )
    monkeypatch.setenv("CLIENTE_FOTOS_DIR", str(tmp_path / "cliente-fotos"))

    files = {"file": ("instalacao.jpg", b"\x89PNG\r\n\x1a\n", "image/png")}
    r = await client.post(
        f"/api/v1/clientes-campo/{cliente.id}/fotos",
        data={"tipo": "instalacao"},
        files=files,
        headers=_auth(token),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["fotos"], list)
    assert len(body["fotos"]) == 1
