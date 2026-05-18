"""Resumo automatico bot->humano (F1).

Quando uma conversa transita pra `ConversaStatus.AGUARDANDO`, o servico monta
um prompt com as ultimas mensagens da conversa e pede ao LLM um TL;DR de 3
linhas (problema, o que o bot tentou, proxima acao). Persiste em
`Conversa.resumo_handoff_encrypted` (Fernet).

Idempotencia: se ja existe resumo e a conversa nao recebeu novas mensagens
desde o ultimo resumo, nao regera.

Falha gracefulle: erro do LLM nao quebra o handoff — apenas loga e segue. O
atendente vai abrir a conversa sem resumo, mas o atendimento nao trava.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    LLMProvider,
    Role,
)
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.db.models.business import Conversa, Mensagem, MensagemRole

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "Voce e um assistente que resume conversas de suporte para o atendente humano "
    "que vai assumir o atendimento. Produza um TL;DR em ate 3 linhas curtas, em "
    "portugues do Brasil, cobrindo:\n"
    "1) Problema relatado pelo cliente.\n"
    "2) O que o bot ja tentou (tools chamadas, info coletada).\n"
    "3) O que o atendente precisa fazer agora.\n\n"
    "Regras estritas:\n"
    "- So cite fatos presentes nas mensagens. Nao infira contrato, pagamento ou "
    "status que nao tenham sido confirmados.\n"
    "- Nao use saudacoes nem assinaturas.\n"
    "- Nao exceda 3 linhas. Cada linha ate ~120 caracteres.\n"
    "- Se nao houver problema claro, escreva apenas: 'Cliente pediu atendimento humano.'"
)

# Quantas mensagens mais recentes alimentam o resumo.
_HISTORY_MAX = 30
# Janela de novas mensagens necessarias pra regerar resumo ja existente.
_MIN_NEW_MSGS_TO_REGEN = 5


def _format_history_for_prompt(mensagens: list[Mensagem]) -> str:
    """Concatena historico em texto simples role: conteudo (mais antigo primeiro)."""
    out: list[str] = []
    for m in mensagens:
        if m.content_encrypted is None:
            continue
        try:
            content = decrypt_pii(m.content_encrypted)
        except Exception:
            content = "<conteudo ilegivel>"
        if m.role is MensagemRole.CLIENTE:
            tag = "Cliente"
        elif m.role is MensagemRole.BOT:
            tag = "Bot"
        elif m.role is MensagemRole.ATENDENTE:
            tag = "Atendente"
        else:
            tag = m.role.value if hasattr(m.role, "value") else str(m.role)
        out.append(f"{tag}: {content}")
    return "\n".join(out)


async def _count_messages_since(
    session: AsyncSession, conversa_id: UUID, since: datetime
) -> int:
    from sqlalchemy import func as sa_func

    stmt = (
        select(sa_func.count())
        .select_from(Mensagem)
        .where(Mensagem.conversa_id == conversa_id, Mensagem.created_at > since)
    )
    return int((await session.execute(stmt)).scalar_one())


async def gerar_resumo_handoff(
    session: AsyncSession,
    conversa_id: UUID,
    provider: LLMProvider,
    *,
    model: str,
) -> str | None:
    """Gera e persiste o resumo. Retorna o resumo gerado, ou `None` se nada foi feito.

    Idempotente: se ja existe resumo recente e nao ha >=5 mensagens novas desde
    entao, nao regera.
    """
    conversa = (
        await session.execute(select(Conversa).where(Conversa.id == conversa_id))
    ).scalar_one_or_none()
    if conversa is None:
        log.warning("handoff_summary.conversa_not_found", conversa_id=str(conversa_id))
        return None

    if conversa.resumo_handoff_at is not None:
        new_msgs = await _count_messages_since(
            session, conversa_id, conversa.resumo_handoff_at
        )
        if new_msgs < _MIN_NEW_MSGS_TO_REGEN:
            log.info(
                "handoff_summary.skip_no_new_messages",
                conversa_id=str(conversa_id),
                new_msgs=new_msgs,
            )
            return None

    msgs_stmt = (
        select(Mensagem)
        .where(Mensagem.conversa_id == conversa_id)
        .order_by(Mensagem.created_at.desc())
        .limit(_HISTORY_MAX)
    )
    rows = list((await session.execute(msgs_stmt)).scalars().all())
    if not rows:
        log.info("handoff_summary.no_messages", conversa_id=str(conversa_id))
        return None
    rows.reverse()
    historico = _format_history_for_prompt(rows)
    if not historico.strip():
        log.info("handoff_summary.empty_history", conversa_id=str(conversa_id))
        return None

    req = ChatRequest(
        model=model,
        messages=[
            ChatMessage(role=Role.SYSTEM, content=_SYSTEM_PROMPT),
            ChatMessage(
                role=Role.USER,
                content=f"Conversa:\n{historico}\n\nResuma em ate 3 linhas.",
            ),
        ],
        temperature=0.0,
    )
    try:
        resp = await provider.chat(req)
    except Exception as e:
        log.warning(
            "handoff_summary.llm_failed",
            conversa_id=str(conversa_id),
            error=str(e),
        )
        return None

    resumo = (resp.content or "").strip()
    if not resumo:
        log.info("handoff_summary.empty_response", conversa_id=str(conversa_id))
        return None

    conversa.resumo_handoff_encrypted = encrypt_pii(resumo)
    conversa.resumo_handoff_at = datetime.now(tz=UTC)
    await session.flush()
    log.info(
        "handoff_summary.done",
        conversa_id=str(conversa_id),
        chars=len(resumo),
    )
    return resumo
