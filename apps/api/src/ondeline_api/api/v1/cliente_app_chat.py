"""Router /api/v1/cliente-app/chat — chat in-app entre cliente e bot.

Fatia 3: tool loop leve com consultar_rede_app (read-only via GenieACS).
Bot responde com texto puro via Hermes. Persistencia em
`cliente_app_messages` separada.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    Role,
    ToolSpec,
)
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
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
from ondeline_api.services.rede_service import RedeService, qualidade_sinal
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/cliente-app/chat", tags=["cliente-app:chat"])

SYSTEM_PROMPT = """Voce e o assistente virtual da Ondeline Telecom, um provedor de internet em Manaus.
Voce conversa com clientes pelo app oficial — eles ja estao autenticados.

Tom: amigavel, direto, em portugues brasileiro informal mas profissional.
Use frases curtas. Sem emojis em excesso (no maximo 1 por resposta).

O que voce pode fazer:
- Tirar duvidas sobre planos, faturas, equipamentos
- Explicar como o cliente acessa cada coisa no app
- Consultar a rede do cliente em tempo real (aparelhos conectados e qualidade
  do sinal da fibra) — use a tool consultar_rede_app quando ele reclamar de
  internet lenta, caindo ou instavel. Traduza o resultado pra linguagem
  simples: sinal "critico" ou "atencao" = problema na fibra do nosso lado
  (oriente abrir chamado na aba Suporte); muitos aparelhos = rede congestionada;
  tudo ok = sugira reiniciar o roteador.

O que voce NAO faz:
- Acessar dados especificos do cliente (plano, fatura) — para isso, pede pro cliente abrir a tab correspondente do app
- Prometer prazos ou descontos
- Cancelar servico (oriente abrir chamado)

Se nao souber, diga que vai pedir pra um atendente humano olhar — e oriente o cliente a abrir um chamado pela tab Suporte > Meus chamados.
"""

MAX_HISTORY = 20  # ultimas N msgs no contexto LLM

_CONSULTAR_REDE_SPEC = ToolSpec(
    name="consultar_rede_app",
    description=(
        "Consulta a rede do cliente logado: quantos aparelhos estao conectados "
        "agora, se a ONU esta online e a qualidade do sinal da fibra. Use quando "
        "o cliente reclamar de internet lenta, caindo ou instavel."
    ),
    parameters={"type": "object", "properties": {}},
)


def _to_out(m: ClienteAppMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=str(m.id),
        role=m.role,
        content=decrypt_pii(m.content_encrypted),
        created_at=m.created_at.isoformat(),
    )


async def _exec_consultar_rede(
    session: AsyncSession, user: ClienteAppUser
) -> dict[str, Any]:
    """Versao app da tool consultar_rede: CPF vem do user autenticado."""
    cpf = decrypt_pii(user.cpf_encrypted) if user.cpf_encrypted else ""
    if not cpf:
        return {"encontrada": False, "motivo": "cpf_indisponivel"}
    s = get_settings()
    redis = await get_redis()
    genie = GenieAcsClient(base_url=s.genieacs_url)
    sgp_ond = await load_sgp_config(session, "ondeline")
    sgp_lnk = await load_sgp_config(session, "linknetam")
    router_sgp = SgpRouter(
        primary=SgpOndelineProvider(**sgp_ond),
        secondary=SgpLinkNetAMProvider(**sgp_lnk),
    )
    cache = SgpCacheService(
        redis=redis,
        session=session,
        router=router_sgp,
        ttl_cliente=s.sgp_cache_ttl_cliente,
        ttl_negativo=s.sgp_cache_ttl_negativo,
    )
    rede = RedeService(session=session, genieacs=genie, sgp_cache=cache)
    try:
        diag = await rede.diagnostico_rede(cpf)
        if not diag.encontrada or diag.device is None:
            return {"encontrada": False, "motivo": diag.motivo}
        d = diag.device
        rx = d.sinal.rx_power if d.sinal else None
        label, emoji = qualidade_sinal(rx)
        return {
            "encontrada": True,
            "online": d.online,
            "aparelhos_conectados": len(d.aparelhos),
            "sinal": {"qualidade": label, "emoji": emoji},
        }
    except GenieAcsUnavailableError:
        return {"erro": "indisponivel"}
    finally:
        await genie.aclose()
        await router_sgp.aclose()


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

    system_msg = ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT)
    history_msgs: list[ChatMessage] = []
    for m in hist:
        # msgs de atendente entram como assistant (LLM ve como historia comum)
        history_msgs.append(
            ChatMessage(
                role=Role.USER if m.role == "user" else Role.ASSISTANT,
                content=decrypt_pii(m.content_encrypted),
            )
        )

    user_llm_msg = ChatMessage(role=Role.USER, content=body.text)

    # 3. Chama LLM (loop de ate 3 iteracoes para tool calls)
    s = get_settings()
    llm_url, llm_key, llm_model = s.effective_llm()
    from ondeline_api.adapters.llm.hermes import HermesProvider

    provider = HermesProvider(
        base_url=llm_url,
        model=llm_model,
        api_key=llm_key,
        timeout=s.llm_timeout_seconds,
    )
    messages: list[ChatMessage] = [system_msg, *history_msgs, user_llm_msg]
    total_tokens = 0
    bot_text: str | None = None
    try:
        for _ in range(3):  # max 3 iteracoes (1 tool + resposta na pratica)
            resp = await provider.chat(
                ChatRequest(
                    model=llm_model,
                    messages=messages,
                    tools=[_CONSULTAR_REDE_SPEC],
                    temperature=0.5,
                )
            )
            total_tokens += resp.tokens_used
            if resp.tool_calls:
                messages = [
                    *messages,
                    ChatMessage(
                        role=Role.ASSISTANT,
                        content=None,
                        tool_calls=list(resp.tool_calls),
                    ),
                ]
                for tc in resp.tool_calls:
                    if tc.name == "consultar_rede_app":
                        result = await _exec_consultar_rede(session, user)
                    else:
                        result = {"erro": "tool_desconhecida"}
                    messages = [
                        *messages,
                        ChatMessage(
                            role=Role.TOOL,
                            content=json.dumps(result, ensure_ascii=False),
                            tool_call_id=tc.id,
                            name=tc.name,
                        ),
                    ]
                continue
            bot_text = resp.content
            break
        if not bot_text:
            bot_text = (
                "Nao consegui completar a consulta agora. Tenta de novo em instantes?"
            )
        tokens: int | None = total_tokens if total_tokens > 0 else None
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
