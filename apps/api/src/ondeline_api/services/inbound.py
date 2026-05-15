"""Servico de processamento de mensagem entrante.

Orquestra: parser -> dedup -> get-or-create conversa -> FSM -> persiste
estado -> enfileira ack outbound. Pura logica; nao toca FastAPI nem Celery
diretamente. Recebe deps via `InboundDeps`. Os Fakes nos testes implementam
a mesma interface estrutural.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import structlog

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    OrdemServico,
    OsStatus,
)
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
    FsmDecision,
)
from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.services.media_classifier import (
    CATEGORIES_ESCALATE,
    CATEGORY_ACK,
    CATEGORY_TAG,
    MediaCategory,
    classify_media,
)
from ondeline_api.webhook.parser import InboundEvent, InboundKind

log = structlog.get_logger(__name__)


class _ConversaRepoProto(Protocol):
    async def get_or_create_by_whatsapp(self, whatsapp: str) -> Conversa: ...
    async def update_estado_status(
        self, conversa: Conversa, *, estado: ConversaEstado, status: ConversaStatus
    ) -> None: ...
    async def set_cliente(self, conversa: Conversa, cliente_id: UUID) -> None: ...
    async def add_tag(self, conversa: Conversa, tag: str) -> None: ...


class _MensagemRepoProto(Protocol):
    async def insert_inbound_or_skip(
        self,
        *,
        conversa_id: UUID,
        external_id: str,
        text: str | None,
        media_type: str | None,
        media_url: str | None,
    ) -> Mensagem | None: ...
    async def insert_bot_reply(
        self, *, conversa_id: UUID, text: str
    ) -> Mensagem: ...


class _OutboundQueueProto(Protocol):
    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None: ...
    def enqueue_llm_turn(self, conversa_id: UUID) -> None: ...
    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None: ...


@dataclass
class InboundDeps:
    conversas: _ConversaRepoProto
    mensagens: _MensagemRepoProto
    outbound: _OutboundQueueProto
    ack_text: str
    redis: Any = field(default=None)  # aioredis.Redis | None — typed Any to keep deps loose
    session: Any = field(default=None)  # AsyncSession | None


@dataclass
class InboundResult:
    conversa_id: UUID | None
    persisted: bool
    duplicate: bool
    escalated: bool
    skipped_reason: str | None = None


_MEDIA_KINDS = {
    InboundKind.IMAGE,
    InboundKind.AUDIO,
    InboundKind.VIDEO,
    InboundKind.DOCUMENT,
}


_CMD_CONCLUIR_RE = re.compile(r"^conclu[ií]r\s+(OS-[\w-]+)\b", re.IGNORECASE)


def _br_local_digits(digits: str) -> str:
    """Normaliza dígitos de número BR para os 8 dígitos locais.

    Tolera: com/sem código de país (55), com/sem DDD, com/sem nono dígito.
    Ex: "559784109856" → "84109856"
        "5597984109856" → "84109856"
        "97984109856" → "84109856"
    """
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = digits[2:]
    if len(digits) == 9 and digits[0] == "9":
        digits = digits[1:]
    return digits


def _to_fsm_event(kind: InboundKind, text: str | None) -> Event:
    if kind is InboundKind.TEXT:
        return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)
    return Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=text)


async def process_inbound_message(
    evt: InboundEvent, deps: InboundDeps
) -> InboundResult:
    if evt.from_me:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="from_me"
        )
    if evt.kind is InboundKind.STICKER:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="sticker"
        )
    if evt.kind is InboundKind.TEXT and not evt.text:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="empty_text"
        )

    conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)

    media_type = evt.kind.value if evt.kind in _MEDIA_KINDS else None
    msg = await deps.mensagens.insert_inbound_or_skip(
        conversa_id=conversa.id,
        external_id=evt.external_id,
        text=evt.text,
        media_type=media_type,
        media_url=None,  # Evolution payload ja entrega midia hospedada; M3 nao baixa
    )
    if msg is None:
        return InboundResult(
            conversa_id=conversa.id, persisted=False, duplicate=True, escalated=False
        )

    # Detecção de comando CONCLUIR OS-* (técnico finaliza OS via WhatsApp).
    # Roda antes da verificação de bot.ativo para que técnicos sempre consigam concluir.
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
    ):
        _m = _CMD_CONCLUIR_RE.match((evt.text or "").strip())
        log.info("concluir.cmd_check", regex_matched=bool(_m))
        if _m:
            codigo = _m.group(1).upper()
            import re as _re

            from sqlalchemy import select as sa_select

            from ondeline_api.db.models.business import Tecnico as TecnicoModel

            # Normaliza para os 8 dígitos locais para tolerar formato antigo/novo do 9° dígito BR.
            jid_digits = _re.sub(r"\D", "", evt.jid)
            jid_local = _br_local_digits(jid_digits)
            tecnicos_all = list(
                (await deps.session.execute(
                    sa_select(TecnicoModel).where(TecnicoModel.whatsapp.isnot(None))
                )).scalars().all()
            )
            tecnico_sender = next(
                (
                    t for t in tecnicos_all
                    if (t_local := _br_local_digits(_re.sub(r"\D", "", t.whatsapp or "")))
                    and len(t_local) == 8
                    and len(jid_local) == 8
                    and jid_local == t_local
                ),
                None,
            )
            log.info(
                "concluir.tecnico_lookup",
                tecnico_found=tecnico_sender is not None,
                codigo=codigo,
            )
            if tecnico_sender is None:
                # Não é técnico — deixa o fluxo normal do bot tratar
                pass
            else:
                os_row = (
                    await deps.session.execute(
                        sa_select(OrdemServico).where(
                            OrdemServico.codigo == codigo,
                            OrdemServico.status.in_(
                                [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
                            ),
                        )
                    )
                ).scalar_one_or_none()
                if os_row is None:
                    deps.outbound.enqueue_send_outbound(
                        evt.jid,
                        f"OS {codigo} não encontrada ou já concluída. Verifique o código e tente novamente.",
                        conversa.id,
                    )
                    return InboundResult(
                        conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                    )
                if os_row.tecnico_id != tecnico_sender.id:
                    deps.outbound.enqueue_send_outbound(
                        evt.jid,
                        f"A OS {codigo} não está atribuída a você.",
                        conversa.id,
                    )
                    return InboundResult(
                        conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                    )
                conversa.checklist_metadata = {
                    "os_id": str(os_row.id),
                    "os_codigo": codigo,
                    "step": 1,
                    "respostas": {},
                }
                await deps.conversas.update_estado_status(
                    conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
                )
                deps.outbound.enqueue_send_outbound(
                    evt.jid,
                    f"✅ OS *{codigo}* encontrada! Vamos registrar a conclusão em 3 passos.\n\n"
                    "1️⃣ *O que foi feito?* Descreva o serviço realizado.",
                    conversa.id,
                )
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )

    # Intercepta CHECKLIST_OS — coleta sequencial de conclusão (3 passos)
    if conversa.estado is ConversaEstado.CHECKLIST_OS and deps.session is not None:
        meta: dict[str, Any] = conversa.checklist_metadata or {}
        step: int = meta.get("step", 1)
        respostas: dict[str, Any] = meta.get("respostas", {})

        # Passo 1: relatorio | Passo 2: houve_visita | Passo 3: materiais (conclusão)
        _PROXIMA: dict[int, str] = {
            1: "2️⃣ *Houve visita presencial?* Responda *SIM* ou *NÃO*.",
            2: "3️⃣ *Materiais / gastos?* (ex: 10m cabo UTP, R$ 25 — ou responda *NENHUM*)",
        }

        if step not in (1, 2, 3):
            conversa.checklist_metadata = None
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Ocorreu um erro no relatório. Envie *CONCLUIR OS-XXXX* novamente para recomeçar.",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        # Passo 2: valida SIM/NÃO
        if step == 2:
            resp = (evt.text or "").strip().upper().replace("Ã", "A")
            if resp not in ("SIM", "NAO", "NÃO"):
                deps.outbound.enqueue_send_outbound(
                    evt.jid, "Por favor, responda apenas *SIM* ou *NÃO*.", conversa.id
                )
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )
            respostas["houve_visita"] = resp in ("SIM",)
        elif step == 1:
            respostas["relatorio"] = (evt.text or "").strip()
        else:  # step == 3
            mat = (evt.text or "").strip()
            respostas["materiais"] = None if mat.upper() == "NENHUM" else mat

        if step < 3:
            conversa.checklist_metadata = {**meta, "step": step + 1, "respostas": respostas}
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(evt.jid, _PROXIMA[step], conversa.id)
        else:
            # Checklist completo — conclui OS nos campos corretos
            os_id = meta.get("os_id")
            codigo = meta.get("os_codigo", "")
            cliente_id_para_followup = None
            if os_id:
                from datetime import UTC as _UTC
                from datetime import datetime as _dt
                from uuid import UUID as _UUID

                from sqlalchemy import select as sa_select
                os_row = (
                    await deps.session.execute(
                        sa_select(OrdemServico).where(OrdemServico.id == _UUID(os_id))
                    )
                ).scalar_one_or_none()
                if os_row:
                    os_row.status = OsStatus.CONCLUIDA
                    os_row.concluida_em = _dt.now(tz=_UTC)
                    os_row.relatorio = respostas.get("relatorio")
                    os_row.houve_visita = respostas.get("houve_visita", True)
                    os_row.materiais = respostas.get("materiais")
                    cliente_id_para_followup = os_row.cliente_id
                    await deps.session.flush()

            conversa.checklist_metadata = None
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                f"✅ *OS {codigo} concluída!* O cliente será notificado em breve. Obrigado! 🙏",
                conversa.id,
            )
            # Envia follow-up para o cliente (conversa do cliente, não do técnico)
            if cliente_id_para_followup is not None:
                from sqlalchemy import select as sa_select

                from ondeline_api.db.models.business import Conversa as ConversaModel
                from ondeline_api.db.models.business import ConversaEstado as CE
                cli_conversa = (
                    await deps.session.execute(
                        sa_select(ConversaModel).where(
                            ConversaModel.cliente_id == cliente_id_para_followup,
                            ConversaModel.estado.notin_([CE.ENCERRADA]),
                        ).order_by(ConversaModel.created_at.desc()).limit(1)
                    )
                ).scalar_one_or_none()
                if cli_conversa:
                    deps.outbound.enqueue_followup_os(cli_conversa.id, resultado="ok", resposta="")

        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # Bloqueia mensagens de clientes quando bot está desativado.
    # Executado APÓS os blocos de CONCLUIR e CHECKLIST_OS para que técnicos
    # sempre possam finalizar OS mesmo com bot desligado.
    if deps.session is not None:
        bot_ativo = await ConfigRepo(deps.session).get("bot.ativo")
        if bot_ativo is False:
            return InboundResult(
                conversa_id=conversa.id,
                persisted=True,
                duplicate=False,
                escalated=False,
                skipped_reason="bot_desativado",
            )

    # Intercepta midia para classificacao antes do FSM
    if evt.kind in _MEDIA_KINDS:
        category = classify_media(evt.kind, evt.text)
        ack = CATEGORY_ACK[category]
        tag = CATEGORY_TAG.get(category)

        if tag:
            await deps.conversas.add_tag(conversa, tag)

        if category is MediaCategory.AUDIO:
            # Nao escala — apenas avisa cliente e continua no estado atual
            deps.outbound.enqueue_send_outbound(evt.jid, ack, conversa.id)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        if category in CATEGORIES_ESCALATE:
            # Avisa cliente e escala para humano
            deps.outbound.enqueue_send_outbound(evt.jid, ack, conversa.id)
            if conversa.transferred_at is None:
                conversa.transferred_at = datetime.now(tz=UTC)
            await deps.conversas.update_estado_status(
                conversa,
                estado=ConversaEstado.AGUARDA_ATENDENTE,
                status=ConversaStatus.AGUARDANDO,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=True
            )

    # Intercepta coleta sequencial de mudanca de endereco
    if conversa.estado is ConversaEstado.MUDANCA_ENDERECO and evt.kind is InboundKind.TEXT:
        addr_meta: dict[str, Any] = conversa.checklist_metadata or {}
        addr_step: str = addr_meta.get("step", "rua")
        addr_dados: dict[str, Any] = addr_meta.get("novo_endereco", {})
        addr_dados[addr_step] = (evt.text or "").strip()

        if addr_step == "referencia":
            # Coleta completa — decide baseado em status financeiro
            endereco_str = (
                f"{addr_dados.get('rua', '')}, {addr_dados.get('bairro', '')}"
                f" — Ref: {addr_dados.get('referencia', 'N/A')}"
            )
            # Verifica status do cliente no cache
            cliente_status = None
            if conversa.cliente_id is not None:
                from sqlalchemy import select as sa_select

                from ondeline_api.db.models.business import Cliente as ClienteModel
                _session = deps.session
                if _session is not None:
                    cli_row = (
                        await _session.execute(
                            sa_select(ClienteModel).where(ClienteModel.id == conversa.cliente_id)
                        )
                    ).scalar_one_or_none()
                    cliente_status = cli_row.status if cli_row else None

            conversa.checklist_metadata = None
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
            )

            if cliente_status and cliente_status.lower() in ("suspenso", "bloqueado", "inadimplente"):
                # Escala com dados já coletados
                msg_escala = (
                    f"Recebi o novo endereço: {endereco_str}. "
                    "Porém há uma pendência financeira no seu contrato. "
                    "Um atendente vai te ajudar com os próximos passos. 🙏"
                )
                deps.outbound.enqueue_send_outbound(evt.jid, msg_escala, conversa.id)
                if conversa.transferred_at is None:
                    conversa.transferred_at = datetime.now(tz=UTC)
                await deps.conversas.update_estado_status(
                    conversa,
                    estado=ConversaEstado.AGUARDA_ATENDENTE,
                    status=ConversaStatus.AGUARDANDO,
                )
            else:
                # Abre OS de mudança via LLM
                msg_ok = (
                    f"Perfeito! Registrei o novo endereço: {endereco_str}. "
                    "Vou criar uma ordem de serviço para a mudança de instalação. "
                    "Em breve nosso técnico entrará em contato! 🔧"
                )
                deps.outbound.enqueue_send_outbound(evt.jid, msg_ok, conversa.id)
                deps.outbound.enqueue_llm_turn(conversa.id)

        else:
            # Próximo passo
            next_step = "bairro" if addr_step == "rua" else "referencia"
            next_question = (
                "Qual é o bairro?"
                if next_step == "bairro"
                else "Algum ponto de referência? (ou responda NENHUM)"
            )
            conversa.checklist_metadata = {**addr_meta, "step": next_step, "novo_endereco": addr_dados}
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.MUDANCA_ENDERECO, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(evt.jid, next_question, conversa.id)

        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    if deps.redis is not None:
        try:
            from ondeline_api.services.conversa_events import publish as _pub
            await _pub(
                deps.redis,
                conversa.id,
                {
                    "type": "msg",
                    "id": str(msg.id),
                    "role": "cliente",
                    "text": evt.text,
                    "ts": msg.created_at.isoformat() if msg.created_at else None,
                },
            )
        except Exception:
            pass

    decision: FsmDecision = Fsm.transition(
        estado=conversa.estado,
        status=conversa.status,
        event=_to_fsm_event(evt.kind, evt.text),
    )
    await deps.conversas.update_estado_status(
        conversa, estado=decision.new_estado, status=decision.new_status
    )

    escalated = False
    llm_turn_requested = False
    for action in decision.actions:
        if action.kind is ActionKind.LLM_TURN:
            llm_turn_requested = True
        elif action.kind is ActionKind.SEND_ACK:
            # Backward compat M3 — nao usado em M4 (FSM nao emite mais SEND_ACK)
            deps.outbound.enqueue_send_outbound(evt.jid, deps.ack_text, conversa.id)
            escalated = True
        elif action.kind is ActionKind.FOLLOWUP_OS_CONFIRMAR:
            deps.outbound.enqueue_followup_os(
                conversa.id, resultado="ok", resposta=evt.text or ""
            )
        elif action.kind is ActionKind.FOLLOWUP_OS_ESCALAR:
            deps.outbound.enqueue_followup_os(
                conversa.id, resultado="nao_ok", resposta=evt.text or ""
            )

    if llm_turn_requested:
        deps.outbound.enqueue_llm_turn(conversa.id)
        escalated = True

    return InboundResult(
        conversa_id=conversa.id,
        persisted=True,
        duplicate=False,
        escalated=escalated,
    )
