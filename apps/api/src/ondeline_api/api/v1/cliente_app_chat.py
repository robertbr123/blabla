"""Router /api/v1/cliente-app/chat — chat in-app entre cliente e bot.

MVP: sem tool calling, sem integracao com sistema de conversas (WhatsApp).
Bot responde com texto puro via Hermes. Persistencia em
`cliente_app_messages` separada.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.llm.base import ChatMessage, ChatRequest, Role
from ondeline_api.adapters.llm.hermes import HermesProvider
from ondeline_api.api.schemas.cliente_app_auth import (
    ChatMessageOut,
    ChatMessagesOut,
    ChatSendIn,
    ChatSendOut,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppMessage, ClienteAppUser
from ondeline_api.deps import get_db

router = APIRouter(prefix="/api/v1/cliente-app/chat", tags=["cliente-app:chat"])

SYSTEM_PROMPT = """Voce e o assistente virtual da Ondeline Telecom, um provedor de internet em Manaus.
Voce conversa com clientes pelo app oficial — eles ja estao autenticados.

Tom: amigavel, direto, em portugues brasileiro informal mas profissional.
Use frases curtas. Sem emojis em excesso (no maximo 1 por resposta).

O que voce pode fazer:
- Tirar duvidas sobre planos, faturas, equipamentos
- Explicar como o cliente acessa cada coisa no app
- Orientar problemas basicos (sem internet → "reinicie o modem", etc)

O que voce NAO faz:
- Acessar dados especificos do cliente (plano, fatura, status) — para isso, pede pro cliente abrir a tab correspondente do app
- Prometer prazos ou descontos
- Cancelar servico (oriente abrir chamado)

Se nao souber, diga que vai pedir pra um atendente humano olhar — e oriente o cliente a abrir um chamado pela tab Suporte > Meus chamados.
"""

MAX_HISTORY = 20  # ultimas N msgs no contexto LLM


def _to_out(m: ClienteAppMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=str(m.id),
        role=m.role,
        content=decrypt_pii(m.content_encrypted),
        created_at=m.created_at.isoformat(),
    )


@router.get("/messages", response_model=ChatMessagesOut)
async def list_messages(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ChatMessagesOut:
    stmt = (
        select(ClienteAppMessage)
        .where(ClienteAppMessage.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppMessage.created_at))
        .limit(limit + 1)
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="cursor invalido") from e
        stmt = stmt.where(ClienteAppMessage.created_at < cursor_dt)

    rows = list((await session.execute(stmt)).scalars())
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = rows[-1].created_at.isoformat()

    return ChatMessagesOut(
        items=[_to_out(m) for m in rows],
        next_cursor=next_cursor,
    )


@router.post("/send", response_model=ChatSendOut)
async def send(
    body: ChatSendIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ChatSendOut:
    # 1. Grava msg do user
    user_msg = ClienteAppMessage(
        cliente_app_user_id=user.id,
        role="user",
        content_encrypted=encrypt_pii(body.text),
    )
    session.add(user_msg)
    await session.flush()
    await session.commit()
    await session.refresh(user_msg)

    # Se atendente assumiu, bot nao responde — atendente conduz via dashboard.
    if user.human_handoff_atendente_id is not None:
        return ChatSendOut(user_message=_to_out(user_msg), bot_message=None)

    # 2. Monta historico (ultimas N msgs, ordem cronologica)
    hist_stmt = (
        select(ClienteAppMessage)
        .where(ClienteAppMessage.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppMessage.created_at))
        .limit(MAX_HISTORY)
    )
    hist = list((await session.execute(hist_stmt)).scalars())
    hist.reverse()  # mais antiga primeiro

    messages: list[ChatMessage] = [ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT)]
    for m in hist:
        # msgs de atendente entram como assistant (LLM ve como historia comum)
        messages.append(
            ChatMessage(
                role=Role.USER if m.role == "user" else Role.ASSISTANT,
                content=decrypt_pii(m.content_encrypted),
            )
        )

    # 3. Chama LLM
    s = get_settings()
    llm_url, llm_key, llm_model = s.effective_llm()
    provider = HermesProvider(
        base_url=llm_url,
        model=llm_model,
        api_key=llm_key,
        timeout=s.llm_timeout_seconds,
    )
    try:
        resp = await provider.chat(
            ChatRequest(model=llm_model, messages=messages, temperature=0.5)
        )
        bot_text = (resp.content or "").strip()
        if not bot_text:
            bot_text = "Desculpe, nao consegui responder agora. Tente de novo em alguns instantes."
        tokens = resp.tokens_used
    except Exception:
        bot_text = "Desculpe, nao consegui me conectar agora. Tente de novo em alguns instantes."
        tokens = None
    finally:
        await provider.aclose()

    # 4. Grava resposta do bot
    bot_msg = ClienteAppMessage(
        cliente_app_user_id=user.id,
        role="bot",
        content_encrypted=encrypt_pii(bot_text),
        llm_tokens_used=tokens,
    )
    session.add(bot_msg)
    await session.flush()
    await session.commit()
    await session.refresh(bot_msg)

    return ChatSendOut(
        user_message=_to_out(user_msg),
        bot_message=_to_out(bot_msg),
    )
