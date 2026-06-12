"""Testes do tool loop do chat in-app (consultar_rede_app).

Monkeypatch strategy:
- HermesProvider: importado inline dentro de `send`, portanto patchado em
  `ondeline_api.api.v1.cliente_app_chat.HermesProvider` (o nome no namespace
  do modulo no momento da execucao).
- _exec_consultar_rede: funcao async module-level patchada diretamente em
  `ondeline_api.api.v1.cliente_app_chat._exec_consultar_rede`.
"""
from __future__ import annotations

import collections.abc
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from ondeline_api.adapters.llm.base import (
    ChatRequest,
    ChatResponse,
    ToolCall,
)
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.passwords import hash_password
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppMessage, ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.main import create_app
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

TEST_CPF = "11144477735"


# ---------------------------------------------------------------------------
# Fake LLM provider
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Provider fake que responde de acordo com a fila de respostas pre-configurada."""

    def __init__(self, responses: list[ChatResponse]) -> None:
        self._queue = list(responses)
        self.calls: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.calls.append(req)
        return self._queue.pop(0)

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_cliente(db_session: AsyncSession) -> ClienteAppUser:
    u = ClienteAppUser(
        cpf_hash=hash_pii(TEST_CPF),
        cpf_last4=TEST_CPF[-4:],
        cpf_encrypted=encrypt_pii(TEST_CPF),
        nome_encrypted=encrypt_pii("Cliente Chat Teste"),
        telefone_encrypted=encrypt_pii("92991234567"),
        password_hash=hash_password("SenhaForte123!"),
        sgp_id="99999",
        status="active",
    )
    db_session.add(u)
    await db_session.commit()
    return u


def _make_app(db_session: AsyncSession) -> FastAPI:
    app = create_app()

    async def _override_db() -> collections.abc.AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    return app


def _auth(u: ClienteAppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_mod.encode_cliente_access_token(u.id)}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_chat_sem_tool(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provider responde texto direto (sem tool_calls) -> msg bot salva corretamente."""
    fake_response = ChatResponse(
        content="Ola! Posso te ajudar com alguma coisa?",
        tool_calls=[],
        tokens_used=42,
        finish_reason="stop",
    )
    fake_provider = _FakeProvider([fake_response])

    def _fake_hermes(
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int,
    ) -> _FakeProvider:
        return fake_provider

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_chat.HermesProvider", _fake_hermes
    )

    app = _make_app(db_session)
    u = await _make_cliente(db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/api/v1/cliente-app/chat/send",
            json={"text": "Oi, tudo bem?"},
            headers=_auth(u),
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bot_message"] is not None
    assert body["bot_message"]["role"] == "bot"
    assert body["bot_message"]["content"] == "Ola! Posso te ajudar com alguma coisa?"
    # provider chamado exatamente 1 vez
    assert len(fake_provider.calls) == 1


async def test_chat_com_consultar_rede(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provider: 1o turno tool_call -> 2o turno texto final.
    Asserts:
    - resposta final salva
    - provider chamado 2 vezes
    - 2a chamada contem msg role TOOL com name consultar_rede_app
    """
    rede_result: dict[str, Any] = {
        "encontrada": True,
        "online": True,
        "aparelhos_conectados": 5,
        "sinal": {"qualidade": "bom", "emoji": "🟢"},
    }

    turno1 = ChatResponse(
        content=None,
        tool_calls=[ToolCall(id="t1", name="consultar_rede_app", arguments={})],
        tokens_used=15,
        finish_reason="tool_calls",
    )
    turno2 = ChatResponse(
        content="Sua rede esta ok — 5 aparelhos conectados, sinal bom.",
        tool_calls=[],
        tokens_used=38,
        finish_reason="stop",
    )
    fake_provider = _FakeProvider([turno1, turno2])

    def _fake_hermes(
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int,
    ) -> _FakeProvider:
        return fake_provider

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_chat.HermesProvider", _fake_hermes
    )

    async def _fake_exec_rede(
        session: AsyncSession, user: ClienteAppUser
    ) -> dict[str, Any]:
        return rede_result

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_chat._exec_consultar_rede",
        _fake_exec_rede,
    )

    app = _make_app(db_session)
    u = await _make_cliente(db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/api/v1/cliente-app/chat/send",
            json={"text": "Minha internet esta lenta"},
            headers=_auth(u),
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bot_message"] is not None
    bot_content = body["bot_message"]["content"]
    assert "5" in bot_content or "rede" in bot_content.lower()

    # provider chamado 2 vezes (1 tool call + 1 resposta final)
    assert len(fake_provider.calls) == 2

    # 2a chamada deve conter uma mensagem role=tool com name=consultar_rede_app
    second_call_msgs = fake_provider.calls[1].messages
    tool_msgs = [m for m in second_call_msgs if m.role == "tool"]
    assert len(tool_msgs) >= 1
    assert tool_msgs[0].name == "consultar_rede_app"
    assert tool_msgs[0].tool_call_id == "t1"


async def test_chat_genieacs_indisponivel(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_exec_consultar_rede retorna erro indisponivel -> bot ainda responde, sem 500."""
    turno1 = ChatResponse(
        content=None,
        tool_calls=[ToolCall(id="t2", name="consultar_rede_app", arguments={})],
        tokens_used=12,
        finish_reason="tool_calls",
    )
    turno2 = ChatResponse(
        content="Nao consegui verificar a rede agora, mas pode abrir um chamado.",
        tool_calls=[],
        tokens_used=30,
        finish_reason="stop",
    )
    fake_provider = _FakeProvider([turno1, turno2])

    def _fake_hermes(
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int,
    ) -> _FakeProvider:
        return fake_provider

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_chat.HermesProvider", _fake_hermes
    )

    async def _fake_exec_indisponivel(
        session: AsyncSession, user: ClienteAppUser
    ) -> dict[str, Any]:
        return {"erro": "indisponivel"}

    monkeypatch.setattr(
        "ondeline_api.api.v1.cliente_app_chat._exec_consultar_rede",
        _fake_exec_indisponivel,
    )

    app = _make_app(db_session)
    u = await _make_cliente(db_session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/api/v1/cliente-app/chat/send",
            json={"text": "Minha internet caiu!"},
            headers=_auth(u),
        )

    # nao explode — bot responde normalmente
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bot_message"] is not None
    assert body["bot_message"]["role"] == "bot"
    # provider chamado 2 vezes: tool call + resposta final com erro incluido no contexto
    assert len(fake_provider.calls) == 2
    # 2a chamada contem mensagem tool com erro serializado
    second_call_msgs = fake_provider.calls[1].messages
    tool_msgs = [m for m in second_call_msgs if m.role == "tool"]
    assert len(tool_msgs) >= 1
    assert "indisponivel" in (tool_msgs[0].content or "")

    # conteudo do bot salvo e decriptavel (db roundtrip ok)
    stmt = (
        select(ClienteAppMessage)
        .where(ClienteAppMessage.cliente_app_user_id == u.id)
        .where(ClienteAppMessage.role == "bot")
        .order_by(desc(ClienteAppMessage.created_at))
        .limit(1)
    )
    row = (await db_session.execute(stmt)).scalar_one()
    assert decrypt_pii(row.content_encrypted) is not None
