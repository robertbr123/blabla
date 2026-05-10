"""Notification sender — render message text + dispatch via Evolution.

Each NotificacaoTipo gets its own template. Messages are intentionally short,
WhatsApp-friendly, with light emoji.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Notificacao,
    NotificacaoTipo,
)
from ondeline_api.repositories.notificacao import NotificacaoRepo

log = structlog.get_logger(__name__)


def _fmt_data(d: str) -> str:
    if d and "-" in d and len(d) >= 10:
        try:
            dt = datetime.fromisoformat(d[:10]).date()
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return d
    return d


def _fmt_valor(v: float | int | str) -> str:
    try:
        return f"R$ {float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return f"R$ {v}"


def render_message(n: Notificacao, cliente_nome: str) -> str:
    payload = n.payload or {}
    _parts = (cliente_nome or "").split()
    nome = _parts[0] if _parts else "Cliente"

    if n.tipo is NotificacaoTipo.VENCIMENTO:
        titulos = payload.get("titulos", [])
        if not titulos:
            return f"Olá, {nome}! 👋 Sua fatura vence em breve. Posso te enviar a 2ª via?"
        primeiro = titulos[0]
        venc = _fmt_data(str(primeiro.get("vencimento", "")))
        valor = _fmt_valor(primeiro.get("valor", 0))
        plural = "s" if len(titulos) > 1 else ""
        return (
            f"Olá, {nome}! 👋\n"
            f"Sua fatura{plural} vence em {venc} (valor: {valor}).\n"
            "Quer que eu te envie o boleto e o PIX agora? 📄"
        )

    if n.tipo is NotificacaoTipo.ATRASO:
        dias = payload.get("dias_atraso", 0)
        return (
            f"Oi {nome}, tudo bem? 😊\n"
            f"Notamos que sua fatura está com {dias} dia(s) de atraso. "
            "Posso te ajudar enviando o boleto + PIX para regularizar?"
        )

    if n.tipo is NotificacaoTipo.PAGAMENTO:
        return (
            f"Olá, {nome}! ✅\n"
            "Confirmamos o pagamento da sua fatura. Obrigado! 🙏"
        )

    if n.tipo is NotificacaoTipo.OS_CONCLUIDA:
        codigo = payload.get("codigo", "")
        return (
            f"Oi {nome}! 👋\n"
            f"Sua OS {codigo} foi concluída há um tempo. Como foi o atendimento? "
            "Responde de 1 a 5 (5 = excelente) que estamos ouvindo! 🌟"
        )

    if n.tipo is NotificacaoTipo.MANUTENCAO:
        titulo = payload.get("titulo", "manutenção planejada")
        inicio = payload.get("inicio_at", "")
        fim = payload.get("fim_at", "")
        try:
            inicio_dt = datetime.fromisoformat(inicio)
            fim_dt = datetime.fromisoformat(fim)
            janela = f"{inicio_dt.strftime('%H:%M')} às {fim_dt.strftime('%H:%M')}"
        except (ValueError, TypeError):
            janela = "em breve"
        return (
            f"Oi {nome}! 🔧\n"
            f"Vamos fazer uma manutenção: {titulo} ({janela}). "
            "Sua internet pode oscilar nesse período. Obrigado pela compreensão!"
        )

    return f"Olá, {nome}! Aviso da Ondeline."


async def send_one(
    session: Any,
    evolution: EvolutionAdapter,
    notificacao: Notificacao,
    cliente: Cliente,
) -> bool:
    """Render + send one notification. Marks as sent or failed.

    Returns True if sent, False if failed (e.g., EvolutionError).
    """
    repo = NotificacaoRepo(session)
    try:
        nome = decrypt_pii(cliente.nome_encrypted) if cliente.nome_encrypted else "Cliente"
    except Exception as e:
        log.warning("notify.decrypt_failed", error=str(e))
        nome = "Cliente"

    if not cliente.whatsapp:
        log.warning("notify.no_whatsapp", notif_id=str(notificacao.id))
        await repo.mark_failed(notificacao)
        return False

    text = render_message(notificacao, nome)
    try:
        await evolution.send_text(cliente.whatsapp, text)
    except EvolutionError as e:
        log.warning("notify.send_failed", notif_id=str(notificacao.id), error=str(e))
        await repo.mark_failed(notificacao)
        return False

    await repo.mark_sent(notificacao)
    log.info("notify.sent", notif_id=str(notificacao.id), tipo=notificacao.tipo.value)
    return True
