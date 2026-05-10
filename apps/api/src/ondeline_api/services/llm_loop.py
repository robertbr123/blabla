"""Loop de tool-calling do LLM.

Recebe a Conversa + ToolContext + LLMProvider. Monta historico (ultimas N
mensagens) + system prompt + tool specs do registry. Itera ate `max_iter`:
  1) chama LLM
  2) se retornou texto sem tool_calls -> envia via Evolution + persiste +
     contabiliza tokens + termina
  3) se retornou tool_calls -> executa cada tool, anexa resultado como
     role=tool, repete

Em qualquer falha (timeout, excecao do provider, budget excedido) escala
para humano via tool transferir_para_humano sintetica + envia mensagem
educada ao cliente.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import structlog

from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMProvider,
    Role,
)
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.pii_mask import mask_pii
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools import registry as tools_registry
from ondeline_api.tools.context import ToolContext

log = structlog.get_logger(__name__)


SYSTEM_PROMPT = (
    "Voce e Ondeline, assistente virtual da Ondeline Telecom (provedor de internet "
    "brasileiro). Atende via WhatsApp de forma simpatica, objetiva e profissional.\n\n"
    "REGRAS ABSOLUTAS:\n"
    "- NUNCA diga que e IA; nunca mencione modelo, gateway ou tecnologia.\n"
    "- Respostas curtas, em portugues brasileiro, com emojis leves.\n"
    "- NAO se reapresente se ja existe historico.\n\n"
    "QUANDO O CLIENTE NAO ESTIVER IDENTIFICADO:\n"
    "- Pergunte o CPF (ou CNPJ) e use a tool buscar_cliente_sgp.\n\n"
    "QUANDO O CLIENTE PEDIR BOLETO/2A VIA/PIX:\n"
    "- Confirme e use a tool enviar_boleto.\n\n"
    "QUANDO O CONTRATO ESTIVER ATIVO E HOUVER PROBLEMA TECNICO:\n"
    "- Tente orientar primeiro (luzes do roteador, reinicio).\n"
    "- Se nao resolver, use a tool abrir_ordem_servico.\n\n"
    "QUANDO PRECISAR ESCALAR (cancelamento, reclamacao formal, negociacao de divida, ou cliente insistir):\n"
    "- Avise o cliente e use a tool transferir_para_humano.\n\n"
    "PLANOS:\n"
    "- Use a tool consultar_planos para responder valores/velocidades.\n\n"
    "MANUTENCOES:\n"
    "- Se o cliente reportar instabilidade, considere consultar_manutencoes(cidade) antes de orientar."
)


@dataclass
class LoopOutcome:
    final_text: str | None
    tokens_used: int
    iterations: int
    tool_calls_made: list[str]
    escalated: bool


def _msg_to_chat(m: Mensagem) -> ChatMessage:
    role = Role.USER if m.role is MensagemRole.CLIENTE else Role.ASSISTANT
    content = decrypt_pii(m.content_encrypted) if m.content_encrypted else "[midia]"
    return ChatMessage(role=role, content=content)


async def run_turn(
    *,
    ctx: ToolContext,
    provider: LLMProvider,
    model: str,
    history_turns: int,
    max_iter: int,
    budget: TokensBudget | None,
) -> LoopOutcome:
    """Roda um turno completo do bot. Retorna LoopOutcome."""
    tool_calls_made: list[str] = []

    if budget is not None and await budget.is_over(str(ctx.conversa.id)):
        return await _force_escalate(ctx, motivo="orcamento de tokens diario excedido")

    history = await MensagemRepo(ctx.session).list_history(
        ctx.conversa.id, limit=history_turns
    )
    messages: list[ChatMessage] = [
        ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
        *(_msg_to_chat(m) for m in history),
    ]

    total_tokens = 0
    for it in range(max_iter):
        try:
            resp: ChatResponse = await provider.chat(
                ChatRequest(
                    model=model,
                    messages=messages,
                    tools=tools_registry.specs(),
                )
            )
        except Exception as e:
            log.warning("llm_loop.provider_error", error=str(e))
            outcome = await _force_escalate(ctx, motivo="falha tecnica temporaria")
            outcome.iterations = it
            return outcome

        total_tokens += resp.tokens_used

        if not resp.tool_calls:
            text = resp.content or ""
            if text.strip():
                masked_log = mask_pii(text[:100])
                log.info("llm_loop.final", text_preview=masked_log, tokens=total_tokens)
                await ctx.evolution.send_text(ctx.conversa.whatsapp, text)
                await MensagemRepo(ctx.session).insert_bot_reply(
                    conversa_id=ctx.conversa.id, text=text
                )
                if budget is not None:
                    await budget.add(str(ctx.conversa.id), total_tokens)
                return LoopOutcome(
                    final_text=text,
                    tokens_used=total_tokens,
                    iterations=it + 1,
                    tool_calls_made=tool_calls_made,
                    escalated=False,
                )
            # texto vazio sem tool_calls — anomalia; encerra com escalation
            outcome = await _force_escalate(ctx, motivo="resposta vazia do modelo")
            outcome.iterations = it + 1
            return outcome

        # Tool calls — anexa msg assistant + executa cada tool
        messages.append(
            ChatMessage(
                role=Role.ASSISTANT,
                content=None,
                tool_calls=list(resp.tool_calls),
            )
        )
        for tc in resp.tool_calls:
            tool_calls_made.append(tc.name)
            result = await tools_registry.invoke(tc.name, ctx, tc.arguments)
            messages.append(
                ChatMessage(
                    role=Role.TOOL,
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=tc.id,
                    name=tc.name,
                )
            )
            # Se a tool foi transferir_para_humano, a Conversa ja mudou — nao faz sentido continuar
            if tc.name == "transferir_para_humano":
                if budget is not None:
                    await budget.add(str(ctx.conversa.id), total_tokens)
                return LoopOutcome(
                    final_text=None,
                    tokens_used=total_tokens,
                    iterations=it + 1,
                    tool_calls_made=tool_calls_made,
                    escalated=True,
                )

    # Max iter exhausted — escalar
    outcome = await _force_escalate(ctx, motivo="loop excedeu max_iter")
    outcome.tokens_used = total_tokens
    outcome.iterations = max_iter
    outcome.tool_calls_made = tool_calls_made
    return outcome


async def _force_escalate(ctx: ToolContext, *, motivo: str) -> LoopOutcome:
    fallback = (
        "Tive um probleminha tecnico aqui. 😅 Vou te passar pra um atendente humano "
        "para te ajudar agora."
    )
    try:
        await ctx.evolution.send_text(ctx.conversa.whatsapp, fallback)
        await MensagemRepo(ctx.session).insert_bot_reply(
            conversa_id=ctx.conversa.id, text=fallback
        )
    except Exception:
        pass
    ctx.conversa.estado = ConversaEstado.AGUARDA_ATENDENTE
    ctx.conversa.status = ConversaStatus.AGUARDANDO
    await ctx.session.flush()
    log.warning("llm_loop.force_escalate", motivo=motivo)
    return LoopOutcome(
        final_text=fallback,
        tokens_used=0,
        iterations=0,
        tool_calls_made=["transferir_para_humano"],
        escalated=True,
    )
