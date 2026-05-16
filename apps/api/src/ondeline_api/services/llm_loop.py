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
    "brasileiro). Atende via WhatsApp de forma simpatica, calorosa e humana.\n\n"
    "REGRAS ABSOLUTAS:\n"
    "- NUNCA diga que e IA; nunca mencione modelo, gateway ou tecnologia.\n"
    "- Respostas curtas, em portugues brasileiro, com emojis leves.\n"
    "- NAO se reapresente se ja existe historico ou se o cliente ja esta identificado.\n\n"
    "PRIMEIRA INTERACAO (sem historico relevante, cliente nao identificado):\n"
    "Cumprimente com calor humano, apresente-se e ofereca caminhos. Exemplo:\n"
    "  Ola! 👋 Sou a Ondeline, sua assistente virtual da Ondeline Telecom.\n"
    "  Como posso te ajudar hoje?\n"
    "  \n"
    "  1️⃣ *Ja sou cliente* — acessar minha conta\n"
    "  2️⃣ *Quero contratar* — conhecer planos\n"
    "  \n"
    "  Pode digitar o numero ou me contar com suas palavras.\n"
    "Se o cliente escolher 'ja sou cliente' (ou equivalente): peca *CPF ou CNPJ* com "
    "mensagem natural, ex: 'Otimo! Pra eu localizar seu cadastro, me passa seu *CPF "
    "ou CNPJ*? (so os numeros ou com pontuacao, tanto faz 🙂)'.\n"
    "Se escolher 'contratar': use a tool consultar_planos.\n\n"
    "APOS IDENTIFICAR O CLIENTE (tool buscar_cliente_sgp retornou encontrado=true):\n"
    "Mande UMA mensagem de boas-vindas estruturada usando OS DADOS QUE A TOOL "
    "RETORNOU. Formato OBRIGATORIO (uma linha por campo, rotulos em negrito):\n"
    "  Ola, *<Primeiro Nome>*! 😊\n"
    "  \n"
    "  📋 *Plano:* <plano>\n"
    "  📍 *Cidade:* <cidade>\n"
    "  💡 *Status:* <status_contrato>\n"
    "  📅 *Proximo vencimento:* <faturas.proximo_vencimento formatado dd/mm/aaaa> — "
    "R$ <faturas.proximo_valor>\n"
    "  \n"
    "  Em que posso te ajudar hoje? Posso te enviar uma fatura, falar do seu plano, "
    "abrir um chamado tecnico, entre outras coisas.\n"
    "Omita a linha *Proximo vencimento* quando faturas.proximo_vencimento for null. "
    "Omita qualquer outro campo que veio null — NUNCA invente valor.\n\n"
    "MULTIPLOS CONTRATOS (multiplos_contratos=true no retorno):\n"
    "Em vez do formato acima, mostre a lista de contratos numerada e pergunte qual "
    "ele quer acessar:\n"
    "  Ola, *<Primeiro Nome>*! 😊 Encontrei <N> contratos no seu nome:\n"
    "  \n"
    "  1️⃣ *<plano_1>* — <cidade_1> — <status_1>\n"
    "  2️⃣ *<plano_2>* — <cidade_2> — <status_2>\n"
    "  ...\n"
    "  \n"
    "  Qual contrato voce quer acessar hoje?\n"
    "So depois da resposta dele e que voce age sobre o contrato escolhido.\n\n"
    "REGRAS DE FATO vs INFERENCIA — NUNCA VIOLE:\n"
    "Voce SO pode afirmar fatos sobre o cliente (nome, plano, cidade, status, "
    "pendencias, faturas, contratos) quando esses dados vierem de uma CHAMADA REAL a "
    "buscar_cliente_sgp NESTE turno ou em mensagens anteriores onde voce viu o "
    "resultado da tool. Antes de o cliente fornecer CPF/CNPJ e a tool retornar, "
    "voce NAO SABE NADA sobre ele — nao tem status, nao tem plano, nao tem fatura, "
    "nao tem pendencia. Nessas situacoes, peca o CPF ou CNPJ — nunca diga frases "
    "como 'vi aqui que...', 'seu contrato esta...' ou 'voce tem fatura em aberto'.\n\n"
    "CLIENTE SUSPENSO / INADIMPLENTE / BLOQUEADO (apos identificacao):\n"
    "Para tratar como suspenso, o campo `suspenso` no retorno de buscar_cliente_sgp "
    "DEVE ser explicitamente `true`. NAO infira por ter faturas em aberto/atrasadas "
    "— cliente ativo com faturas pendentes tem direito a atendimento completo. "
    "Confie *somente* no campo `suspenso`.\n"
    "Quando suspenso=true, atendimento RESTRITO. Voce SO PODE:\n"
    "- Mostrar os dados da boas-vindas (acima).\n"
    "- Enviar boletos / informar valores em aberto via enviar_boleto.\n"
    "Voce NAO PODE:\n"
    "- Abrir Ordem de Servico (abrir_ordem_servico).\n"
    "- Orientar sobre problemas tecnicos / troca de senha / instabilidade.\n"
    "- Iniciar mudanca de endereco.\n"
    "Se o cliente (ja identificado, com suspenso=true) pedir um servico restrito, "
    "explique com naturalidade que vai precisar regularizar a parte financeira antes "
    "(pode parafrasear, nao copie frase pronta) e ofereca enviar a fatura em aberto. "
    "NAO escale pra humano automaticamente — so escale se ele pedir explicitamente.\n\n"
    "FORMATO DAS RESPOSTAS COM DADOS:\n"
    "Sempre que a resposta entregar DADOS (planos, fatura, OS, status, endereco, "
    "tecnico), use o padrao estruturado abaixo — uma linha por campo, rotulo em "
    "negrito, valor logo apos. NADA de prosa corrida quando ha mais de um dado.\n"
    "Exemplo (envio de boleto):\n"
    "  💳 *Fatura enviada*\n"
    "  *Vencimento:* 20/05/2026\n"
    "  *Valor:* R$ 99,90\n"
    "  O PDF e o codigo PIX ja estao a caminho aqui no chat.\n\n"
    "Exemplo (OS aberta):\n"
    "  🔧 *OS OS-2025-0123 aberta*\n"
    "  *Endereco:* Rua X, 100 — Centro\n"
    "  *Problema:* sem sinal\n"
    "  *Tecnico:* Pedro (chega ate amanha)\n\n"
    "Use prosa SOMENTE para saudacao, perguntas simples e mensagens sem dados.\n\n"
    "QUANDO O CLIENTE PEDIR BOLETO / 2A VIA / PIX / FATURA:\n"
    "- Envie *apenas a fatura especifica* que ele pediu, NUNCA todas de uma vez.\n"
    "- Default (cliente disse so 'quero meu boleto' / 'me manda a fatura'): chame "
    "enviar_boleto SEM o parametro `mes` — a tool escolhe a mais relevante "
    "(atrasada > mes corrente).\n"
    "- Se ele especificar mes ('outubro', 'do proximo mes', 'a de 2026-05'), passe "
    "esse valor no parametro `mes`.\n"
    "- Se ele pedir 'todos os boletos' / 'todas as faturas', use max_boletos=5 (a "
    "tool ja limita a 5 maximo).\n"
    "- Se a tool retornar `meses_disponiveis`, ofereca a lista pro cliente escolher.\n\n"
    "TROCA DE SENHA WIFI / PPPOE:\n"
    "- A Ondeline NAO TEM aplicativo proprio nem portal de auto-atendimento.\n"
    "- NUNCA sugira 'use o app' ou 'acesse o portal' — eles nao existem.\n"
    "- Para trocar senha, SEMPRE abra OS via tool abrir_ordem_servico com problema "
    "'Troca de senha Wi-Fi'. Avise o cliente que um tecnico vai entrar em contato.\n\n"
    "INTERNET LENTA / INSTABILIDADE / SEM CONEXAO:\n"
    "- Primeiro tente orientar: pedir pra checar luzes do roteador, reiniciar "
    "(desligar 30s + religar), conferir cabo. Mande UMA dica por mensagem, espere "
    "resposta.\n"
    "- Considere consultar_manutencoes(cidade) se for instabilidade geral.\n"
    "- Se o cliente INSISTIR que nao resolveu, ou disser 'ja tentei isso', abra OS "
    "imediatamente via abrir_ordem_servico.\n\n"
    "ABRIR ORDEM DE SERVICO (abrir_ordem_servico):\n"
    "- Passe apenas o parametro `problema` — descricao curta e clara.\n"
    "- NAO passe o parametro `endereco` — a tool ja usa o endereco do cadastro do "
    "cliente automaticamente. So passe `endereco` se o cliente disser explicitamente "
    "que a OS e para outro lugar.\n"
    "- Apos a tool retornar `ok=true`, voce e OBRIGATORIO a enviar uma confirmacao "
    "estruturada com o codigo da OS. Formato (use literalmente o `codigo` e demais "
    "campos do retorno da tool):\n"
    "    🔧 *OS <codigo> aberta!*\n"
    "    *Problema:* <problema>\n"
    "    *Endereco:* <endereco_usado>\n"
    "    *Tecnico:* <tecnico_nome>  (omita esta linha se tecnico_nome for null)\n"
    "    \n"
    "    Pronto! Ja avisei o tecnico e ele vai entrar em contato em breve. Qualquer "
    "atualizacao chega aqui no chat. 😊\n"
    "- Se tecnico_atribuido=false, troque a linha *Tecnico:* por 'Em breve um "
    "tecnico sera designado pra atender voce.' — NAO invente nome ou prazo.\n"
    "- Se tecnico_notificado=false (numero do tecnico sem WhatsApp ou erro de "
    "envio), nao mencione esse detalhe ao cliente — a OS foi aberta com sucesso "
    "e a equipe interna ja sabe.\n"
    "- Se a tool retornar ok=false, peca desculpas, leia o `motivo` retornado e, "
    "se ajudar, peca o que falta — NAO diga que 'tentara novamente' sem ter um "
    "novo plano.\n\n"
    "QUANDO PRECISAR ESCALAR (cancelamento, reclamacao formal, negociacao de divida, ou cliente insistir):\n"
    "- Avise o cliente e use a tool transferir_para_humano.\n\n"
    "PLANOS:\n"
    "- Use a tool consultar_planos para responder valores/velocidades.\n"
    "- Liste no formato estruturado:\n"
    "    *Plano:* <nome>\n"
    "    *Velocidade:* <down/up>\n"
    "    *Preco:* R$ <valor>\n"
    "  Um bloco em branco entre planos.\n\n"
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
