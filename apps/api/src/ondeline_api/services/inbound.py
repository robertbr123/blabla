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
from ondeline_api.services import business_hours
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
    def enqueue_media_download(
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


_CMD_CONCLUIR_RE = re.compile(
    # Aceita: CONCLUIR OS-1234, concluir os 1234, finalizar OS-1234, finalizar 1234
    r"^(?:conclu[ií]r|finaliz[a-z]+|encerrar|fechar|terminar)\s+(?:OS[\s-]*)?([A-Za-z0-9][\w-]*)\b",
    re.IGNORECASE,
)
# F10 — detecta "Indicado por XXXXX" como inicio de mensagem.
_CMD_INDICADO_RE = re.compile(
    r"^indicad[oa]\s+por\s+([A-Z0-9]{4,16})\b", re.IGNORECASE
)


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


async def _find_tecnico_ativo_by_jid(session: Any, jid: str) -> Any | None:
    """Resolve um Tecnico ATIVO pelo JID Evolution (ex.: 5597...@s.whatsapp.net).

    Faz matching pelos 8 digitos locais (ignora DDI, DDD, nono digito) — mesma
    logica que os handlers ESTOQUE/CONCLUIR ja usam. Retorna None se nenhum
    bater ou se o tecnico estiver inativo.
    """
    if session is None or not jid:
        return None
    from sqlalchemy import select as _sa_sel

    from ondeline_api.db.models.business import Tecnico as _TecModel

    jid_digits = re.sub(r"\D", "", jid)
    jid_local = _br_local_digits(jid_digits)
    if len(jid_local) != 8:
        return None
    rows = list(
        (
            await session.execute(
                _sa_sel(_TecModel).where(
                    _TecModel.whatsapp.isnot(None), _TecModel.ativo.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    for t in rows:
        t_local = _br_local_digits(re.sub(r"\D", "", t.whatsapp or ""))
        if len(t_local) == 8 and t_local == jid_local:
            return t
    return None


def _to_fsm_event(kind: InboundKind, text: str | None) -> Event:
    if kind is InboundKind.TEXT:
        return Event(kind=EventKind.MSG_CLIENTE_TEXT, text=text)
    return Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=text)


# F12 — Hard gate de identificacao. Quando cliente nao identificado esta em
# estado de coleta inicial e manda mensagem que NAO contem CPF, opcao 1/2 nem
# palavra-chave de contratacao/escape, NAO chamamos LLM — repetimos pedido fixo
# pra ele se identificar. Evita LLM "conversar" sem ter cliente_id.
_GATE_ESTADOS = frozenset({
    ConversaEstado.AGUARDA_OPCAO,
    ConversaEstado.CLIENTE_CPF,
    ConversaEstado.LEAD_NOME,
    ConversaEstado.LEAD_INTERESSE,
})

_RE_OPCAO_12 = re.compile(r"(?:^|\s)[12](?:$|\s|[.,!])")
_RE_QUER_CONTRATAR = re.compile(
    r"\b(contrat|quero (?:ser cliente|internet|plano|fibra)|novo cliente|"
    r"interesse|plano|fibra|mbps|velocidade|valor do plano|quanto custa)\b",
    re.IGNORECASE,
)
_RE_JA_CLIENTE = re.compile(
    r"\b(sou cliente|j[aá] sou|cliente antigo|tenho internet de voc[eê]s)\b",
    re.IGNORECASE,
)
_RE_ESCAPE_HUMANO = re.compile(
    r"\b(atendente|humano|sac|falar com algu[eé]m|suporte)\b",
    re.IGNORECASE,
)

_GATE_MSG = (
    "Pra continuar preciso te identificar 🙋\n\n"
    "Digite seu *CPF* (somente números, 11 dígitos) se já é cliente, "
    "ou *2* se quer contratar um plano."
)


def _mensagem_identifica_ou_libera(text: str | None) -> bool:
    """True se a mensagem traz CPF, opcao 1/2 ou palavra-chave que justifica
    seguir pro LLM. False = bloqueia e repete o pedido."""
    t = (text or "").strip()
    if not t:
        return False
    digits = re.sub(r"\D", "", t)
    if len(digits) >= 11:  # CPF (11) ou CNPJ (14) presentes
        return True
    if _RE_OPCAO_12.search(f" {t} "):
        return True
    if _RE_QUER_CONTRATAR.search(t):
        return True
    if _RE_JA_CLIENTE.search(t):
        return True
    if _RE_ESCAPE_HUMANO.search(t):
        return True
    return False


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
                        serial=m.get("serial"),  # preenchido no step 45 pra serializados
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

    # Follow-up estruturado pro cliente: cuidado pelo Beat schedule_followup_os.
    # NÃO chamamos enqueue_followup_os direto aqui — antes isso enviava só
    # "Fico feliz que tenha resolvido" (genérico) pulando a pergunta inicial.
    # Agora deixamos o Beat agendar a Notificacao OS_CONCLUIDA estruturada
    # 10min após a conclusão (com código, problema, e pedido de CSAT 1-5).
    _ = cliente_id_para_followup  # mantido pra futura integração


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
    if step not in (1, 2, 3, 4, 45, 5):
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

        # Persiste matches em metadata. Itens serializados ficam com serial=None
        # e vão ser preenchidos no passo 45.
        matches_serializaveis = [
            {
                "item_id": str(m.item_id),
                "sku": m.sku,
                "nome": m.nome,
                "quantidade": m.quantidade,
                "saldo_atual": m.saldo_atual,
                "serializado": m.serializado,
                "serial": None,
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

        # Se há itens serializados sem serial preenchido → step 45 (coleta).
        serializados_pendentes = [
            i for i, m in enumerate(matches_serializaveis) if m["serializado"]
        ]
        if serializados_pendentes:
            idx = serializados_pendentes[0]
            item_pendente = matches_serializaveis[idx]
            conversa.checklist_metadata = {
                **meta,
                "step": 45,
                "respostas": respostas,
                "serial_idx": idx,
            }
            await deps.conversas.update_estado_status(
                conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
            )
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                f"📝 Qual o *serial* do *{item_pendente['nome']}*?\n"
                "_(digite o número de série; pra cancelar a baixa, mande PULAR)_"
                + avisos,
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        # Sem serializados → direto pro step 5 de confirmação.
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

    # ── Step 45: coleta de serial pra item serializado ────────
    if step == 45:
        idx = meta.get("serial_idx", 0)
        matches_list: list[dict[str, Any]] = respostas.get(
            "materiais_confirmados", []
        )
        if idx >= len(matches_list):
            # Inconsistência — pula pra confirmação.
            conversa.checklist_metadata = {**meta, "step": 5}
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                "Vamos pra confirmação. Responda *SIM* pra baixar do estoque.",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        item_atual = matches_list[idx]
        serial_input = text.strip()

        # Atalho: PULAR remove o item da baixa (técnico não quer registrar).
        if serial_input.upper() == "PULAR":
            matches_list.pop(idx)
            respostas["materiais_confirmados"] = matches_list
        else:
            if not serial_input:
                deps.outbound.enqueue_send_outbound(
                    evt.jid,
                    f"Serial não pode ser vazio. Qual o serial do *{item_atual['nome']}*? "
                    "(ou mande PULAR pra não registrar este item)",
                    conversa.id,
                )
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )
            # Salva o serial. Não validamos duplicado aqui — o registrar_movimento
            # vai validar de novo na hora da baixa.
            matches_list[idx]["serial"] = serial_input
            respostas["materiais_confirmados"] = matches_list

        # Procura próximo serializado sem serial.
        proximo_idx = next(
            (
                i
                for i, m in enumerate(matches_list)
                if m.get("serializado") and not m.get("serial")
            ),
            None,
        )
        if proximo_idx is not None:
            item_pendente = matches_list[proximo_idx]
            conversa.checklist_metadata = {
                **meta,
                "step": 45,
                "respostas": respostas,
                "serial_idx": proximo_idx,
            }
            deps.outbound.enqueue_send_outbound(
                evt.jid,
                f"📝 E o *serial* do *{item_pendente['nome']}*?\n"
                "_(ou PULAR pra não registrar este item)_",
                conversa.id,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        # Todos os seriais coletados → step 5.
        if not matches_list:
            # Caso o técnico tenha PULADO tudo.
            respostas["materiais_confirmados"] = []
            await _concluir_os_e_baixar_estoque(conversa, deps, meta, respostas)
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )
        conversa.checklist_metadata = {**meta, "step": 5, "respostas": respostas}
        await deps.conversas.update_estado_status(
            conversa, estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT
        )
        from ondeline_api.services.material_concluir import render_resumo_baixa_dict

        deps.outbound.enqueue_send_outbound(
            evt.jid,
            "5️⃣ *Vou baixar do seu estoque:*\n"
            + render_resumo_baixa_dict(matches_list)
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

    # F4 / Cloud API — resolve canal pelo identificador do payload.
    # Evolution traz `evt.instance`, Cloud API traz `evt.cloud_phone_id`.
    # Se nao encontrado, cai pro canal default (slug='suporte') OU ``None``
    # se nada estiver setup.
    canal_id: UUID | None = None
    if deps.session is not None:
        from ondeline_api.repositories.canal import CanalRepo as _CanalRepo

        canal_repo = _CanalRepo(deps.session)
        canal = None
        if evt.cloud_phone_id:
            canal = await canal_repo.get_by_cloud_phone_id(evt.cloud_phone_id)
        elif evt.instance:
            canal = await canal_repo.get_by_evolution_instance(evt.instance)
        if canal is None and (evt.instance or evt.cloud_phone_id):
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

    # Midia inbound (foto/audio/video/doc): seta URL servivel desde ja — assim
    # o evento SSE e qualquer refetch nao correm contra o download async — e
    # enfileira o download dos bytes via worker (provider-aware Evolution/Cloud).
    if media_type is not None:
        msg.media_url = f"/api/v1/conversas/{conversa.id}/media/{msg.id}"
        media_key: dict[str, Any]
        if evt.media_id:
            media_key = {"media_id": evt.media_id}
        else:
            media_key = {
                "id": evt.external_id,
                "remoteJid": evt.jid,
                "fromMe": False,
            }
        deps.outbound.enqueue_media_download(
            mensagem_id=msg.id,
            conversa_id=conversa.id,
            message_key=media_key,
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

    # F10 — comando INDICAR (cliente identificado pede link de indicação).
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
        and conversa.cliente_id is not None
        and evt.text.strip().upper() in ("INDICAR", "INDICACAO", "INDICAÇÃO", "INDICAR AMIGO")
    ):
        from ondeline_api.config import get_settings as _gs2
        from ondeline_api.repositories.indicacao import IndicacaoRepo

        repo_ind = IndicacaoRepo(deps.session)
        ind = await repo_ind.get_or_create_para_cliente(conversa.cliente_id)
        # Monta link wa.me apontando pra mesma instancia.
        settings_ind = _gs2()
        numero_alvo = settings_ind.evolution_instance  # fallback
        # Permite override via config 'indicacao.whatsapp_alvo' (admin pode
        # configurar o numero E.164 sem '+').
        from sqlalchemy import select as _sel2

        from ondeline_api.db.models.business import Config as _CfgModel

        cfg_row = (
            await deps.session.execute(
                _sel2(_CfgModel).where(_CfgModel.key == "indicacao.whatsapp_alvo")
            )
        ).scalar_one_or_none()
        if cfg_row is not None:
            v = cfg_row.value
            if isinstance(v, dict) and "value" in v:
                v = v["value"]
            if isinstance(v, str) and v.strip():
                numero_alvo = v.strip()
        # Sanitiza
        numero_alvo_digits = "".join(c for c in numero_alvo if c.isdigit())
        texto_pre = f"Indicado por {ind.codigo} — quero contratar"
        from urllib.parse import quote

        link = (
            f"https://wa.me/{numero_alvo_digits}?text={quote(texto_pre)}"
            if numero_alvo_digits
            else "(número não configurado — admin precisa setar `indicacao.whatsapp_alvo` no /config)"
        )
        msg_txt = (
            "🎁 *Indique e ganhe!*\n\n"
            f"Seu código: *{ind.codigo}*\n\n"
            "Compartilhe este link com seus amigos:\n"
            f"{link}\n\n"
            "Quando o amigo fechar plano, vocês dois ganham desconto na próxima fatura. ✨"
        )
        deps.outbound.enqueue_send_outbound(evt.jid, msg_txt, conversa.id)
        return InboundResult(
            conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
        )

    # F10 — detecta "Indicado por XXXXXX" no texto da primeira mensagem do lead.
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
        and conversa.cliente_id is None  # só leads / não identificados
    ):
        _m_ind = _CMD_INDICADO_RE.match((evt.text or "").strip())
        if _m_ind:
            codigo_ind = _m_ind.group(1).upper()
            from ondeline_api.repositories.indicacao import IndicacaoRepo

            ind_lead = await IndicacaoRepo(deps.session).get_by_codigo(codigo_ind)
            if ind_lead is not None:
                # Marca a conversa com a indicação (via tags pra audit).
                try:
                    await deps.conversas.add_tag(conversa, f"indicado:{codigo_ind}")
                except Exception:
                    pass
                # Cria Lead vinculado e registra uso.
                from ondeline_api.db.models.business import Lead, LeadStatus

                lead = Lead(
                    nome=evt.push_name or "Lead via indicação",
                    whatsapp=evt.jid,
                    interesse=f"Indicado por {codigo_ind}",
                    status=LeadStatus.NOVO,
                    indicacao_id=ind_lead.id,
                )
                deps.session.add(lead)
                await deps.session.flush()
                await IndicacaoRepo(deps.session).registrar_uso(
                    ind_lead.id, lead_id=lead.id
                )
                _ind_retorno = (
                    "Em instantes um atendente vai falar com você sobre os planos disponíveis."
                    if business_hours.is_open()
                    else business_hours.closed_notice()
                )
                deps.outbound.enqueue_send_outbound(
                    evt.jid,
                    "🎁 Bem-vindo(a)! Você foi indicado por um cliente nosso. "
                    f"{_ind_retorno} "
                    "Quando fechar, vocês dois ganham desconto. ✨",
                    conversa.id,
                )
                # Escala pra humano (comercial).
                from datetime import UTC as _UTC2
                from datetime import datetime as _dt2

                if conversa.transferred_at is None:
                    conversa.transferred_at = _dt2.now(tz=_UTC2)
                await deps.conversas.update_estado_status(
                    conversa,
                    estado=ConversaEstado.AGUARDA_ATENDENTE,
                    status=ConversaStatus.AGUARDANDO,
                )
                return InboundResult(
                    conversa_id=conversa.id,
                    persisted=True,
                    duplicate=False,
                    escalated=True,
                )

    # F11 — comando ESTOQUE (técnico consulta saldo via WhatsApp).
    # Detecta antes do CONCLUIR pra não conflitar com outras palavras.
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
        and (evt.text or "").strip().upper() in ("ESTOQUE", "MEU ESTOQUE", "SALDO")
    ):
        import re as _re

        from sqlalchemy import select as _sa_sel

        from ondeline_api.db.models.business import Tecnico as _TecModel
        from ondeline_api.repositories.estoque import MovimentoRepo as _MovRepo

        jid_digits = _re.sub(r"\D", "", evt.jid)
        jid_local = _br_local_digits(jid_digits)
        tecnicos_all = list(
            (
                await deps.session.execute(
                    _sa_sel(_TecModel).where(_TecModel.whatsapp.isnot(None))
                )
            )
            .scalars()
            .all()
        )
        tec = next(
            (
                t
                for t in tecnicos_all
                if (t_local := _br_local_digits(_re.sub(r"\D", "", t.whatsapp or "")))
                and len(t_local) == 8
                and len(jid_local) == 8
                and jid_local == t_local
            ),
            None,
        )
        if tec is not None:
            saldos = await _MovRepo(deps.session).saldo_full_por_tecnico(tec.id)
            com_saldo = [(it, s) for it, s in saldos if s > 0]
            if not com_saldo:
                msg_txt = (
                    f"📦 *Seu estoque, {tec.nome.split()[0] if tec.nome else 'tec'}*\n\n"
                    "_(vazio — sem itens em estoque)_\n\n"
                    "Pra dar entrada, peça pro admin no painel."
                )
            else:
                linhas = [
                    f"• *{it.nome}*: {s}" + (" (serial)" if it.serializado else "")
                    for it, s in com_saldo
                ]
                msg_txt = (
                    f"📦 *Seu estoque, {tec.nome.split()[0] if tec.nome else 'tec'}*\n\n"
                    + "\n".join(linhas)
                )
            deps.outbound.enqueue_send_outbound(evt.jid, msg_txt, conversa.id)
            return InboundResult(
                conversa_id=conversa.id,
                persisted=True,
                duplicate=False,
                escalated=False,
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
            # Pre-fixa OS- se tecnico digitou so o numero (regex aceita ambas formas).
            if not codigo.startswith("OS-") and not codigo.startswith("OS"):
                codigo = f"OS-{codigo}"
            elif codigo.startswith("OS") and not codigo.startswith("OS-"):
                # 'OS1234' → 'OS-1234'
                codigo = "OS-" + codigo[2:].lstrip("-")
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

    # Intercepta CHECKLIST_OS — coleta sequencial de conclusão.
    # Passos:
    #   1) relatório textual
    #   2) houve visita presencial? SIM/NÃO
    #   3) houve gasto de material? SIM/NÃO (mostra estoque do técnico)
    #   4) lista materiais: "2 conector, 100m cabo"
    #   45) coleta seriais (só se 4 teve itens serializados)
    #   5) confirmação do que vai baixar
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

    # F13 — Short-circuit do tecnico. Se quem enviou eh um Tecnico ATIVO e a
    # mensagem nao casou com nenhum comando especifico (ESTOQUE/CONCLUIR/
    # INDICADO/CHECKLIST_OS ja teriam retornado cedo), respondemos com menu
    # determinitistico de comandos. NAO chamamos LLM nem aplicamos gate F12 —
    # tecnico nao eh cliente.
    if (
        evt.kind is InboundKind.TEXT
        and evt.text
        and deps.session is not None
    ):
        tec = await _find_tecnico_ativo_by_jid(deps.session, evt.jid)
        if tec is not None:
            txt_upper = (evt.text or "").strip().upper()
            primeiro_nome = tec.nome.split()[0] if tec.nome else "tec"

            # MINHAS OS — lista OSs abertas atribuidas a esse tecnico
            if txt_upper in ("MINHAS OS", "MINHAS-OS", "MINHAS_OS", "OS"):
                from sqlalchemy import select as _sa_sel2

                from ondeline_api.db.models.business import (
                    OrdemServico as _OS,
                )

                os_rows = list(
                    (
                        await deps.session.execute(
                            _sa_sel2(_OS).where(
                                _OS.tecnico_id == tec.id,
                                _OS.status.in_(
                                    [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
                                ),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                if not os_rows:
                    msg_txt = (
                        f"📋 *Suas OS, {primeiro_nome}*\n\n"
                        "_(nenhuma OS em aberto atribuida a voce)_"
                    )
                else:
                    linhas = [
                        f"• *{o.codigo}* — {o.status.value} — "
                        f"{(o.problema or '')[:50]}"
                        for o in os_rows
                    ]
                    msg_txt = (
                        f"📋 *Suas OS, {primeiro_nome}*\n\n" + "\n".join(linhas)
                    )
                deps.outbound.enqueue_send_outbound(evt.jid, msg_txt, conversa.id)
                return InboundResult(
                    conversa_id=conversa.id,
                    persisted=True,
                    duplicate=False,
                    escalated=False,
                )

            # Catch-all: menu de AJUDA. NAO chama LLM, NAO escala.
            msg_txt = (
                f"👷 Oi, *{primeiro_nome}*! Comandos disponíveis:\n\n"
                "• *ESTOQUE* — ver seu saldo de equipamentos\n"
                "• *MINHAS OS* — OSs em aberto atribuidas a voce\n"
                "• *CONCLUIR OS-1234* — finalizar uma OS\n"
                "• *AJUDA* — esta lista"
            )
            deps.outbound.enqueue_send_outbound(evt.jid, msg_txt, conversa.id)
            return InboundResult(
                conversa_id=conversa.id,
                persisted=True,
                duplicate=False,
                escalated=False,
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

            # Sem ACK explicito — a transcricao + resposta do LLM levam ~3-8s,
            # tempo suficiente pro cliente perceber o "digitando..." no WhatsApp.
            # ACK gerava ruido em conversas com varios audios seguidos.
            msg.transcricao_status = "pending"
            # message_key shape e provider-especifico: Evolution usa o trio
            # {id, remoteJid, fromMe}; Cloud usa {media_id}. O ASR worker passa
            # esse dict opaco direto pro adapter.get_media_base64.
            message_key: dict[str, Any]
            if evt.media_id:
                message_key = {"media_id": evt.media_id}
            else:
                message_key = {
                    "id": evt.external_id,
                    "remoteJid": evt.jid,
                    "fromMe": False,
                }
            deps.outbound.enqueue_asr(
                mensagem_id=msg.id,
                conversa_id=conversa.id,
                message_key=message_key,
            )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
            )

        if category in CATEGORIES_ESCALATE:
            # Avisa cliente e escala para humano. A expectativa de retorno
            # depende do horário comercial (fora do expediente não promete humano
            # imediato).
            ack_escala = f"{ack} {business_hours.handoff_phrase()}"
            deps.outbound.enqueue_send_outbound(evt.jid, ack_escala, conversa.id)
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
                    + business_hours.humano_message(
                        "Um atendente vai te ajudar com os próximos passos. 🙏"
                    )
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
                    "media_type": msg.media_type,
                    "media_url": msg.media_url,
                    "ts": msg.created_at.isoformat() if msg.created_at else None,
                },
            )
        except Exception:
            pass

    # F12 — Gate de identificacao: se ja pedimos opcao/CPF antes (estado
    # AGUARDA_OPCAO/CLIENTE_CPF/LEAD_*) e cliente segue sem CPF/opcao/palavra
    # de fluxo, NAO deixamos o LLM conversar. Repetimos o pedido determinis-
    # ticamente. Cobre so mensagem TEXT — media segue caminho normal.
    if (
        evt.kind is InboundKind.TEXT
        and conversa.cliente_id is None
        and conversa.estado in _GATE_ESTADOS
        and not _mensagem_identifica_ou_libera(evt.text)
    ):
        log.info(
            "inbound.identificacao_gate.blocked",
            conversa_id=str(conversa.id),
            estado=conversa.estado.value,
        )
        deps.outbound.enqueue_send_outbound(evt.jid, _GATE_MSG, conversa.id)
        # Estado nao muda — continua aguardando identificacao.
        return InboundResult(
            conversa_id=conversa.id,
            persisted=True,
            duplicate=False,
            escalated=False,
        )

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
            _ack_msg = (
                deps.ack_text
                if business_hours.is_open()
                else f"Olá! 😊 Recebi sua mensagem. {business_hours.closed_notice()}"
            )
            deps.outbound.enqueue_send_outbound(evt.jid, _ack_msg, conversa.id)
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
