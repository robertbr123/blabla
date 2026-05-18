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
    async def get_or_create_by_whatsapp(
        self, whatsapp: str, *, canal_id: UUID | None = None
    ) -> Conversa: ...
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
    def enqueue_handoff_summary(self, conversa_id: UUID) -> None: ...
    def enqueue_asr(
        self,
        *,
        mensagem_id: UUID,
        conversa_id: UUID,
        message_key: dict[str, Any] | None = None,
    ) -> None: ...


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


def _extract_audio_seconds(evt: InboundEvent) -> int | None:
    """Tenta extrair duracao do audioMessage. Hoje o parser nao expoe isso —
    quando expusermos no InboundEvent, este helper passa a devolver o valor.
    Por enquanto sempre None (sem limite no inbound; ASR worker valida tamanho)."""
    # Atributo opcional no evento; ausente no schema atual → None.
    return getattr(evt, "audio_seconds", None)


def _yes_no(text: str) -> bool | None:
    """Normaliza SIM/NÃO/S/N (com acentos)."""
    t = (text or "").strip().upper().replace("Ã", "A")
    if t in ("SIM", "S", "YES", "Y"):
        return True
    if t in ("NAO", "NÃO", "N", "NO", "NENHUM"):
        return False
    return None


async def _concluir_os_e_baixar_estoque(
    conversa: Conversa,
    deps: InboundDeps,
    meta: dict[str, Any],
    respostas: dict[str, Any],
) -> None:
    """Conclui a OS, registra movimentos de saída pra cada material confirmado,
    e dispara follow-up pro cliente. Idempotente em caso de retry parcial.
    """
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from uuid import UUID as _UUID

    from sqlalchemy import select as sa_select

    from ondeline_api.db.models.business import Conversa as ConversaModel
    from ondeline_api.db.models.business import ConversaEstado as CE
    from ondeline_api.services.estoque import registrar_movimento

    assert deps.session is not None
    os_id = meta.get("os_id")
    tecnico_id_str = meta.get("tecnico_id")
    codigo = meta.get("os_codigo", "")
    cliente_id_para_followup = None
    materiais_confirmados: list[dict[str, Any]] = respostas.get(
        "materiais_confirmados", []
    )

    if os_id:
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

    # Baixa estoque: cria 1 saida por material confirmado, com ordem_servico_id.
    if tecnico_id_str and materiais_confirmados and os_id:
        # Resolve user_id de quem criou a OS (admin/atendente que importou ou seed).
        # Para movimento pelo WhatsApp, usamos o User do tecnico_user vinculado.
        # Se não houver user vinculado, usa o admin seed (mesmo conceito de "criado_por
        # técnico" via WhatsApp não tem User da sessão JWT).
        # Pegamos o tecnico → tecnico.user_id; senão fallback ao primeiro admin.
        from ondeline_api.db.models.business import Tecnico as _Tec
        from ondeline_api.db.models.identity import Role as _Role
        from ondeline_api.db.models.identity import User as _User

        tec_row = (
            await deps.session.execute(
                sa_select(_Tec).where(_Tec.id == _UUID(tecnico_id_str))
            )
        ).scalar_one_or_none()
        criado_por_id = tec_row.user_id if tec_row and tec_row.user_id else None
        if criado_por_id is None:
            criado_por_id = (
                await deps.session.execute(
                    sa_select(_User.id).where(_User.role == _Role.ADMIN).limit(1)
                )
            ).scalar_one_or_none()

        if criado_por_id is not None:
            for m in materiais_confirmados:
                try:
                    await registrar_movimento(
                        deps.session,
                        item_id=_UUID(m["item_id"]),
                        tipo="saida",
                        quantidade=int(m["quantidade"]),
                        criado_por=criado_por_id,
                        tecnico_id=_UUID(tecnico_id_str),
                        serial=None,  # baixa por quantidade via WhatsApp
                        ordem_servico_id=_UUID(os_id),
                        observacao=f"OS {codigo} concluída via WhatsApp",
                    )
                except Exception as e:
                    log.warning(
                        "checklist.baixa_estoque_falhou",
                        item_id=m.get("item_id"),
                        error=str(e),
                    )

    conversa.checklist_metadata = None
    await deps.conversas.update_estado_status(
        conversa, estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )

    msg_final = f"✅ *OS {codigo} concluída!* O cliente será notificado em breve."
    if materiais_confirmados:
        msg_final += "\n📦 Estoque atualizado."
    msg_final += " Obrigado! 🙏"
    deps.outbound.enqueue_send_outbound(conversa.whatsapp, msg_final, conversa.id)

    # Follow-up pro cliente
    if cliente_id_para_followup is not None:
        cli_conversa = (
            await deps.session.execute(
                sa_select(ConversaModel)
                .where(
                    ConversaModel.cliente_id == cliente_id_para_followup,
                    ConversaModel.estado.notin_([CE.ENCERRADA]),
                )
                .order_by(ConversaModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if cli_conversa:
            deps.outbound.enqueue_followup_os(
                cli_conversa.id, resultado="ok", resposta=""
            )


async def _handle_checklist_step(
    evt: InboundEvent, conversa: Conversa, deps: InboundDeps
) -> InboundResult:
    """Roteia entrada para o passo atual do checklist de conclusão.

    Steps:
      1 → recebe relatório → pergunta visita
      2 → recebe SIM/NÃO visita → pergunta material
      3 → recebe SIM/NÃO material → se NÃO conclui, se SIM pede lista
      4 → recebe lista de materiais → parseia + casa → pede confirmação
      5 → recebe SIM/NÃO confirmação → SIM conclui, NÃO volta pra 4
    """
    from ondeline_api.repositories.estoque import MovimentoRepo
    from ondeline_api.services.material_concluir import (
        parse_e_casar_materiais,
        render_lista_estoque,
        render_resumo_baixa,
    )

    assert deps.session is not None
    meta: dict[str, Any] = conversa.checklist_metadata or {}
    step: int = meta.get("step", 1)
    respostas: dict[str, Any] = meta.get("respostas", {})
    tecnico_id_str = meta.get("tecnico_id")
    text = (evt.text or "").strip()

    # Sanidade: step fora do range = reset.
    if step not in (1, 2, 3, 4, 5):
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

    # ── Step 1: relatório ─────────────────────────────────────
    if step == 1:
        respostas["relatorio"] = text
        conversa.checklist_metadata = {**meta, "step": 2, "respostas": respostas}
        await deps.conversas.update_estado_status(
            conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
        )
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "2️⃣ *Houve visita presencial?* Responda *SIM* ou *NÃO*.",
            conversa.id,
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # ── Step 2: houve visita ──────────────────────────────────
    if step == 2:
        yn = _yes_no(text)
        if yn is None:
            deps.outbound.enqueue_send_outbound(
                evt.jid, "Responda apenas *SIM* ou *NÃO*.", conversa.id
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        respostas["houve_visita"] = yn

        # Vai pro step 3 perguntando sobre material — mostrando estoque atual.
        estoque_txt = "_(sem itens)_"
        if tecnico_id_str:
            from uuid import UUID as _UUID

            saldo_full = await MovimentoRepo(deps.session).saldo_full_por_tecnico(
                _UUID(tecnico_id_str)
            )
            estoque_txt = render_lista_estoque(saldo_full)

        conversa.checklist_metadata = {**meta, "step": 3, "respostas": respostas}
        await deps.conversas.update_estado_status(
            conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
        )
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "3️⃣ *Houve gasto de material?* (*SIM* / *NÃO*)\n\n"
            "Seu estoque atual:\n" + estoque_txt,
            conversa.id,
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # ── Step 3: houve gasto de material? ──────────────────────
    if step == 3:
        yn = _yes_no(text)
        if yn is None:
            deps.outbound.enqueue_send_outbound(
                evt.jid, "Responda apenas *SIM* ou *NÃO*.", conversa.id
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        if not yn:
            # Sem material — conclui OS direto.
            respostas["materiais"] = None
            respostas["materiais_confirmados"] = []
            meta["step"] = 5  # marca como concluído pra função final
            meta["respostas"] = respostas
            conversa.checklist_metadata = meta
            await _concluir_os_e_baixar_estoque(conversa, deps, meta, respostas)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        # SIM — vai pro step 4 pedindo a lista.
        conversa.checklist_metadata = {**meta, "step": 4, "respostas": respostas}
        await deps.conversas.update_estado_status(
            conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
        )
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "4️⃣ *Quais materiais usou?* Liste no formato *quantidade nome*, "
            "separados por vírgula.\n\n"
            "_Exemplos:_\n"
            "• `2 conector, 100m cabo`\n"
            "• `1 onu, 3 conector`\n\n"
            "Para itens com serial (ex: ONU/roteador), use o PWA — aqui é só por quantidade.",
            conversa.id,
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # ── Step 4: lista de materiais ────────────────────────────
    if step == 4:
        # Atalho: "NENHUM" pula a baixa de estoque e conclui.
        if text.upper() in ("NENHUM", "NADA"):
            respostas["materiais"] = None
            respostas["materiais_confirmados"] = []
            await _concluir_os_e_baixar_estoque(conversa, deps, meta, respostas)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        if not tecnico_id_str:
            # Sem tecnico_id no metadata (caso muito improvável) — reset.
            conversa.checklist_metadata = None
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Erro de contexto. Mande *CONCLUIR OS-XXXX* de novo.",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        from uuid import UUID as _UUID

        result = await parse_e_casar_materiais(
            deps.session, tecnico_id=_UUID(tecnico_id_str), texto=text
        )
        # Se NADA casou e teve linhas inválidas/não-encontradas → pede pra reescrever.
        if not result.matches and (
            result.nao_encontrados or result.invalidos or result.sem_saldo
        ):
            msg = "Não consegui interpretar todos os itens. "
            partes: list[str] = []
            if result.invalidos:
                partes.append(
                    "*Não entendi:* " + ", ".join(f"`{x}`" for x in result.invalidos)
                )
            if result.nao_encontrados:
                partes.append(
                    "*Não tem no seu estoque:* "
                    + ", ".join(f"`{x}`" for x in result.nao_encontrados)
                )
            if result.sem_saldo:
                partes.append(
                    "*Saldo insuficiente:* "
                    + ", ".join(
                        f"`{n}` (pediu {q}, tem {s})"
                        for n, q, s in result.sem_saldo
                    )
                )
            msg += "\n" + "\n".join(partes)
            msg += "\n\nMande a lista de novo no formato *quantidade nome*."
            deps.outbound.enqueue_send_outbound(evt.jid, msg, conversa.id)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        if not result.matches:
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Não consegui identificar nenhum item. Tente de novo: *quantidade nome*. "
                "Ex: `2 conector, 100m cabo`. Ou responda *NENHUM* se não houve gasto.",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        # Persiste matches em metadata pra confirmação.
        matches_serializaveis = [
            {
                "item_id": str(m.item_id),
                "sku": m.sku,
                "nome": m.nome,
                "quantidade": m.quantidade,
                "saldo_atual": m.saldo_atual,
            }
            for m in result.matches
        ]
        respostas["materiais"] = text  # texto cru também
        respostas["materiais_confirmados"] = matches_serializaveis

        avisos = ""
        if result.nao_encontrados or result.invalidos or result.sem_saldo:
            avisos_partes: list[str] = []
            if result.nao_encontrados:
                avisos_partes.append(
                    "_Ignorados (não tem no estoque):_ "
                    + ", ".join(result.nao_encontrados)
                )
            if result.invalidos:
                avisos_partes.append(
                    "_Ignorados (formato):_ " + ", ".join(result.invalidos)
                )
            if result.sem_saldo:
                avisos_partes.append(
                    "_Ignorados (sem saldo):_ "
                    + ", ".join(
                        f"{n} pediu {q} tem {s}" for n, q, s in result.sem_saldo
                    )
                )
            avisos = "\n\n⚠️ " + "\n".join(avisos_partes)

        conversa.checklist_metadata = {**meta, "step": 5, "respostas": respostas}
        await deps.conversas.update_estado_status(
            conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
        )
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "5️⃣ *Vou baixar do seu estoque:*\n"
            + render_resumo_baixa(result.matches)
            + avisos
            + "\n\nConfirma? Responda *SIM* ou *NÃO* (não vai baixar nada).",
            conversa.id,
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # ── Step 5: confirmação da baixa ──────────────────────────
    # step == 5
    yn = _yes_no(text)
    if yn is None:
        deps.outbound.enqueue_send_outbound(
            evt.jid, "Responda apenas *SIM* ou *NÃO*.", conversa.id
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )
    if not yn:
        # NÃO — descarta matches e volta pro step 4.
        respostas["materiais_confirmados"] = []
        conversa.checklist_metadata = {**meta, "step": 4, "respostas": respostas}
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "Ok, ignorei a lista. Mande a lista corrigida no formato *quantidade nome* "
            "(ou *NENHUM* pra concluir sem baixa).",
            conversa.id,
        )
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # SIM — conclui e baixa estoque.
    await _concluir_os_e_baixar_estoque(conversa, deps, meta, respostas)
    return InboundResult(
        conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
    )


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

    # F4 — resolve canal pelo `instance` do payload Evolution. Se nao encontrado,
    # cai pro canal default (slug='suporte') OU ``None`` se nada estiver setup.
    canal_id: UUID | None = None
    if deps.session is not None and evt.instance:
        from ondeline_api.repositories.canal import CanalRepo as _CanalRepo

        canal_repo = _CanalRepo(deps.session)
        canal = await canal_repo.get_by_evolution_instance(evt.instance)
        if canal is None:
            # fallback pro canal default
            canal = await canal_repo.get_by_slug("suporte")
        if canal is not None:
            canal_id = canal.id

    conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid, canal_id=canal_id)

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

    # F2 — opt-out de cobrança via WhatsApp.
    # Cliente responde "PARAR" / "SAIR" / "VOLTAR" / "RECEBER" pra
    # desligar/religar lembretes. So funciona se a conversa ja esta vinculada
    # a um Cliente identificado.
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
        and conversa.cliente_id is not None
    ):
        cmd = (evt.text or "").strip().upper()
        if cmd in ("PARAR", "SAIR", "PARA", "STOP"):
            from sqlalchemy import select as _sa_select

            from ondeline_api.db.models.business import Cliente as _Cliente
            from ondeline_api.observability.metrics import cobranca_optout_total

            cli = (
                await deps.session.execute(
                    _sa_select(_Cliente).where(_Cliente.id == conversa.cliente_id)
                )
            ).scalar_one_or_none()
            if cli is not None and not cli.cobranca_optout:
                cli.cobranca_optout = True
                cli.cobranca_optout_at = datetime.now(tz=UTC)
                await deps.session.flush()
                cobranca_optout_total.inc()
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Ok, não enviaremos mais lembretes de cobrança. "
                "Para voltar a receber, responda *VOLTAR* a qualquer momento. "
                "Se quiser falar com a gente, é só mandar mensagem aqui mesmo.",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        if cmd in ("VOLTAR", "RECEBER", "ATIVAR"):
            from sqlalchemy import select as _sa_select

            from ondeline_api.db.models.business import Cliente as _Cliente

            cli = (
                await deps.session.execute(
                    _sa_select(_Cliente).where(_Cliente.id == conversa.cliente_id)
                )
            ).scalar_one_or_none()
            if cli is not None and cli.cobranca_optout:
                cli.cobranca_optout = False
                cli.cobranca_optout_at = None
                await deps.session.flush()
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Pronto! Voltamos a enviar lembretes de cobrança. 👍",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
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
                    "tecnico_id": str(tecnico_sender.id),
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

    # Intercepta CHECKLIST_OS — coleta sequencial de conclusão (5 passos).
    # Passos:
    #   1) relatório textual
    #   2) houve visita presencial? SIM/NÃO
    #   3) houve gasto de material? SIM/NÃO (mostra estoque do técnico)
    #   4) lista materiais (só se 3=SIM): "2 conector, 100m cabo"
    #   5) confirmação do que vai baixar (só se 4 teve matches)
    if conversa.estado is ConversaEstado.CHECKLIST_OS and deps.session is not None:
        return await _handle_checklist_step(evt, conversa, deps)

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
            # F7 — transcricao via OpenAI Whisper.
            # 1) Aviso LGPD na primeira vez que esse cliente manda audio.
            # 2) ACK imediato ("ouvindo seu audio").
            # 3) Enfileira task na fila `asr` que baixa o audio, transcreve,
            #    persiste em mensagens.transcricao_* e dispara llm_turn.
            from ondeline_api.config import get_settings as _gs

            _settings = _gs()
            if not _settings.openai_api_key:
                # Sem chave configurada → fallback antigo (so ACK, sem transcricao).
                deps.outbound.enqueue_send_outbound(evt.jid, ack, conversa.id)
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )

            # Limite de duração: audios > openai_asr_max_seconds são pulados.
            # A Evolution payload normalmente traz `seconds` no audioMessage.
            audio_seconds = _extract_audio_seconds(evt)
            if (
                audio_seconds is not None
                and audio_seconds > _settings.openai_asr_max_seconds
            ):
                deps.outbound.enqueue_send_outbound(
                    evt.jid,
                    "Recebi seu áudio, mas ele é longo demais pra transcrição "
                    "automática. Pode me resumir por texto? 🙏",
                    conversa.id,
                )
                msg.transcricao_status = "skipped"
                from ondeline_api.observability.metrics import (
                    asr_skipped_total,
                )

                asr_skipped_total.labels(motivo="limite_duracao").inc()
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )

            # Aviso LGPD (1x por cliente identificado).
            if (
                conversa.cliente_id is not None
                and deps.session is not None
            ):
                from sqlalchemy import select as _sel

                from ondeline_api.db.models.business import Cliente as _Cli

                cli = (
                    await deps.session.execute(
                        _sel(_Cli).where(_Cli.id == conversa.cliente_id)
                    )
                ).scalar_one_or_none()
                if cli is not None and cli.asr_aviso_enviado_at is None:
                    deps.outbound.enqueue_send_outbound(
                        evt.jid,
                        "_(Aviso: usamos transcrição automática pra te atender "
                        "mais rápido. Seu áudio é processado pela OpenAI e "
                        "descartado em seguida. Se preferir, escreva por texto.)_",
                        conversa.id,
                    )
                    cli.asr_aviso_enviado_at = datetime.now(tz=UTC)
                    await deps.session.flush()

            # ACK imediato + marca mensagem como pending + enfileira ASR.
            deps.outbound.enqueue_send_outbound(
                evt.jid, "🎧 Recebi seu áudio, vou ouvir e já respondo.", conversa.id
            )
            msg.transcricao_status = "pending"
            deps.outbound.enqueue_asr(
                mensagem_id=msg.id,
                conversa_id=conversa.id,
                message_key={
                    "id": evt.external_id,
                    "remoteJid": evt.jid,
                    "fromMe": False,
                },
            )
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
            deps.outbound.enqueue_handoff_summary(conversa.id)
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
                deps.outbound.enqueue_handoff_summary(conversa.id)
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
    prev_status = conversa.status
    await deps.conversas.update_estado_status(
        conversa, estado=decision.new_estado, status=decision.new_status
    )
    if (
        decision.new_status is ConversaStatus.AGUARDANDO
        and prev_status is not ConversaStatus.AGUARDANDO
    ):
        deps.outbound.enqueue_handoff_summary(conversa.id)

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
