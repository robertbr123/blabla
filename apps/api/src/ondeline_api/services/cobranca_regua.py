"""F2 — Régua de cobrança automática via WhatsApp.

Beat job diário (09:00 BRT) varre clientes ativos com fatura em aberto no SGP,
decide o gatilho aplicável (D-3, D+1, D+5, D+15) e envia boleto PDF + Pix
copia-e-cola + QR (via Pix QR de F3, opcional). Respeita opt-out por cliente
e limite de 1 lembrete/dia/cliente.

Idempotência: tabela `cobranca_lembrete` com UNIQUE(cliente_id, fatura_id,
gatilho) garante que o mesmo gatilho nao dispara 2x na mesma fatura.

Falha gracefulle por cliente: erro num cliente nao derruba o batch.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.observability.metrics import (
    cobranca_lembrete_enviado_total,
    cobranca_lembrete_skipped_total,
)
from ondeline_api.repositories.cobranca import CobrancaRepo
from ondeline_api.services.pix_qr import enviar_pix_qr_best_effort
from ondeline_api.services.sgp_cache import SgpCacheService

log = structlog.get_logger(__name__)

# Gatilhos: dias em relação ao vencimento.
# Positivo = atraso. Negativo = antes do vencimento.
GATILHOS: dict[str, int] = {
    "D-3": -3,
    "D+1": 1,
    "D+5": 5,
    "D+15": 15,
}

# Ordem de prioridade (mais grave primeiro) — quando 2 gatilhos casam na
# mesma fatura no mesmo dia, mandamos só o mais grave.
GATILHO_PRIORIDADE = ["D+15", "D+5", "D+1", "D-3"]

# Limite operacional: máx 1 lembrete por cliente por dia.
MAX_LEMBRETES_POR_DIA_CLIENTE = 1


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _venc_to_date(t: Fatura) -> date | None:
    try:
        return datetime.fromisoformat(t.vencimento).date()
    except (ValueError, AttributeError):
        return None


def _decide_gatilho(fatura: Fatura, today: date) -> str | None:
    """Retorna o gatilho que casa exatamente hoje, ou None.

    D-3: vencimento == today + 3 dias.
    D+1, D+5, D+15: vencimento == today - N dias (atraso).
    """
    venc = _venc_to_date(fatura)
    if venc is None:
        return None
    delta = (today - venc).days  # positivo = atraso
    for gatilho, offset in GATILHOS.items():
        if delta == offset:
            return gatilho
    return None


def _escolher_lembrete_do_dia(
    faturas: list[Fatura], today: date
) -> tuple[Fatura, str] | None:
    """Entre as faturas em aberto, escolhe (fatura, gatilho) mais grave do dia.

    Retorna None se nenhuma fatura casa com gatilho hoje.
    """
    candidatos: list[tuple[Fatura, str]] = []
    for f in faturas:
        gat = _decide_gatilho(f, today)
        if gat is not None:
            candidatos.append((f, gat))
    if not candidatos:
        return None
    # Mais grave primeiro.
    prio = {g: i for i, g in enumerate(GATILHO_PRIORIDADE)}
    candidatos.sort(key=lambda x: prio.get(x[1], 99))
    return candidatos[0]


def _render_mensagem(gatilho: str, nome: str, fatura: Fatura) -> str:
    """Template curto, em portugues do Brasil, leve uso de emoji."""
    venc_br = ""
    if fatura.vencimento and len(fatura.vencimento) >= 10:
        y, m, d = fatura.vencimento[:10].split("-")
        venc_br = f"{d}/{m}/{y}"
    valor_br = f"R$ {fatura.valor:.2f}".replace(".", ",")
    first = nome.split()[0] if nome else "Cliente"

    if gatilho == "D-3":
        return (
            f"Olá, {first}! 👋\n"
            f"Lembrete amigável: sua fatura vence em *3 dias* ({venc_br}).\n"
            f"Valor: *{valor_br}*.\n"
            "Segue o boleto + Pix. Pra parar de receber, responda *PARAR*."
        )
    if gatilho == "D+1":
        return (
            f"Oi {first}, tudo bem? 😊\n"
            f"Sua fatura venceu ontem ({venc_br}).\n"
            f"Valor: *{valor_br}*.\n"
            "Segue o boleto + Pix pra regularizar. Pra parar, responda *PARAR*."
        )
    if gatilho == "D+5":
        return (
            f"Olá, {first}.\n"
            f"Sua fatura está com *5 dias de atraso* (venc. {venc_br}, *{valor_br}*).\n"
            "Evite a suspensão do serviço — segue o boleto + Pix.\n"
            "Pra parar de receber lembretes, responda *PARAR*."
        )
    # D+15
    return (
        f"Olá, {first}.\n"
        f"⚠️ *Aviso final* antes da suspensão: fatura com *15 dias de atraso* "
        f"(venc. {venc_br}, *{valor_br}*).\n"
        "Segue o boleto + Pix. Se já pagou, desconsidere.\n"
        "Pra parar de receber, responda *PARAR*."
    )


async def _enviar_lembrete(
    *,
    session: AsyncSession,
    evolution: EvolutionAdapter,
    redis: Any,
    cliente: Cliente,
    fatura: Fatura,
    gatilho: str,
    nome: str,
) -> bool:
    """Envia mensagem + PDF + Pix copia-e-cola + QR (best-effort). Retorna True
    se a mensagem principal foi entregue (PDF/QR sao best-effort)."""
    texto = _render_mensagem(gatilho, nome, fatura)
    try:
        await evolution.send_text(cliente.whatsapp, texto)
    except EvolutionError as e:
        log.warning(
            "cobranca.send_text_failed",
            cliente_id=str(cliente.id),
            gatilho=gatilho,
            error=str(e),
        )
        return False

    # PDF best effort
    if fatura.link_pdf:
        try:
            await evolution.send_media(
                cliente.whatsapp,
                url=fatura.link_pdf,
                mediatype="document",
                mimetype="application/pdf",
                file_name=f"fatura_{fatura.vencimento or fatura.id}.pdf",
                caption="Boleto",
            )
        except EvolutionError as e:
            log.warning("cobranca.send_pdf_failed", error=str(e))

    # Pix QR + copia-e-cola (F3, best-effort)
    await enviar_pix_qr_best_effort(
        evolution=evolution,
        redis=redis,
        jid=cliente.whatsapp,
        codigo_pix_sgp=fatura.codigo_pix,
        valor=fatura.valor,
        fatura_id=fatura.id,
        session=session,
    )
    return True


async def run_regua(
    session: AsyncSession,
    *,
    evolution: EvolutionAdapter,
    sgp_cache: SgpCacheService,
    redis: Any,
) -> dict[str, int]:
    """Executa 1 passada da régua. Idempotente — pode ser re-rodada no mesmo dia."""
    today = _today()
    repo = CobrancaRepo(session)

    stmt = select(Cliente).where(
        Cliente.deleted_at.is_(None),
        Cliente.cobranca_optout.is_(False),
    )
    clientes = list((await session.execute(stmt)).scalars().all())

    enviados = 0
    pulados_optout = 0
    pulados_rate = 0
    pulados_ja_enviado = 0
    pulados_sem_fatura = 0
    falhas = 0

    for cliente in clientes:
        if not cliente.whatsapp:
            continue
        try:
            cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        except Exception:
            continue
        try:
            cli_sgp = await sgp_cache.get_cliente(cpf)
        except Exception as e:
            log.warning("cobranca.sgp_failed", cliente_id=str(cliente.id), error=str(e))
            continue
        if cli_sgp is None:
            pulados_sem_fatura += 1
            continue
        abertas = [t for t in cli_sgp.titulos if t.status == "aberto"]
        if not abertas:
            pulados_sem_fatura += 1
            continue

        escolha = _escolher_lembrete_do_dia(abertas, today)
        if escolha is None:
            continue
        fatura, gatilho = escolha

        # Rate limit por cliente/dia.
        if await repo.enviados_hoje_por_cliente(cliente.id, today) >= MAX_LEMBRETES_POR_DIA_CLIENTE:
            pulados_rate += 1
            cobranca_lembrete_skipped_total.labels(motivo="rate_limit").inc()
            continue

        # Idempotência via UNIQUE.
        ja = await repo.ja_enviado(cliente.id, fatura.id, gatilho)
        if ja:
            pulados_ja_enviado += 1
            cobranca_lembrete_skipped_total.labels(motivo="ja_enviado").inc()
            continue

        nome = ""
        try:
            nome = decrypt_pii(cliente.nome_encrypted) if cliente.nome_encrypted else ""
        except Exception:
            nome = ""

        ok = await _enviar_lembrete(
            session=session,
            evolution=evolution,
            redis=redis,
            cliente=cliente,
            fatura=fatura,
            gatilho=gatilho,
            nome=nome,
        )
        if not ok:
            falhas += 1
            cobranca_lembrete_skipped_total.labels(motivo="falha_envio").inc()
            continue

        venc = _venc_to_date(fatura)
        if venc is None:
            continue
        registered = await repo.registrar(
            cliente_id=cliente.id,
            fatura_id=fatura.id,
            gatilho=gatilho,
            vencimento=venc,
        )
        if registered is not None:
            enviados += 1
            cobranca_lembrete_enviado_total.labels(gatilho=gatilho).inc()

    log.info(
        "cobranca.regua.done",
        enviados=enviados,
        pulados_rate=pulados_rate,
        pulados_ja_enviado=pulados_ja_enviado,
        pulados_sem_fatura=pulados_sem_fatura,
        pulados_optout=pulados_optout,
        falhas=falhas,
    )
    return {
        "enviados": enviados,
        "pulados_rate": pulados_rate,
        "pulados_ja_enviado": pulados_ja_enviado,
        "pulados_sem_fatura": pulados_sem_fatura,
        "falhas": falhas,
    }
