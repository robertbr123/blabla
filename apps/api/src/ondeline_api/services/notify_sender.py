"""Notification sender — render message text + dispatch via Evolution.

Each NotificacaoTipo gets its own template. Messages are intentionally short,
WhatsApp-friendly, with light emoji.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from ondeline_api.adapters.whatsapp import (
    CloudAdapter,
    WhatsAppAdapter,
    WhatsAppError,
)
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    ConversaEstado,
    Notificacao,
    NotificacaoTipo,
)
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.notificacao import NotificacaoRepo
from ondeline_api.services.whatsapp_message_log import extract_wamid, record_sent
from ondeline_api.services.whatsapp_templates import spec_for

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
        problema = payload.get("problema", "")
        linha_problema = f"*Problema atendido:* {problema}\n" if problema else ""
        return (
            f"Oi {nome}! 👋\n\n"
            f"✅ *OS {codigo} concluída pelo técnico!*\n"
            f"{linha_problema}"
            "\nFicou tudo certo? Responde:\n"
            "• *SIM* — ficou ok\n"
            "• *NÃO* — ainda tem algum problema\n\n"
            "Se ficou bom, aproveita e me dá uma nota de 1 a 5 (5 = excelente) 🌟"
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
    adapter: WhatsAppAdapter,
    notificacao: Notificacao,
    cliente: Cliente,
) -> bool:
    """Render + send one notification. Marks as sent or failed.

    Estrategia provider-aware:
    - Cloud (Meta) + spec de template existe: envia TEMPLATE (unica forma fora
      da janela 24h). Se falhar com NotImplementedError, cai pra texto livre
      (defesa contra bug de wiring).
    - Evolution OU spec ausente: render_message() + send_text.

    Returns True if sent, False if failed.
    """
    repo = NotificacaoRepo(session)
    try:
        nome_full = decrypt_pii(cliente.nome_encrypted) if cliente.nome_encrypted else "Cliente"
    except Exception as e:
        log.warning("notify.decrypt_failed", error=str(e))
        nome_full = "Cliente"
    nome_parts = (nome_full or "").split()
    primeiro_nome = nome_parts[0] if nome_parts else "Cliente"

    if not cliente.whatsapp:
        log.warning("notify.no_whatsapp", notif_id=str(notificacao.id))
        await repo.mark_failed(notificacao)
        return False

    spec = spec_for(notificacao.tipo)
    use_template = isinstance(adapter, CloudAdapter) and spec is not None

    try:
        if use_template and spec is not None:
            body_params = spec.body_params_fn(notificacao, primeiro_nome)
            header_media: tuple[str, str] | None = None
            if spec.header_media_fn is not None:
                header_media = spec.header_media_fn(notificacao)
            send_result = await adapter.send_template(
                cliente.whatsapp,
                name=spec.name,
                language=spec.language,
                body_params=body_params,
                header_media_url=header_media[0] if header_media else None,
                header_media_type=header_media[1] if header_media else None,
            )
            log.info(
                "notify.sent_template",
                notif_id=str(notificacao.id),
                template=spec.name,
            )
            # Persiste wamid + template pra metricas (Fase 2.2). Falha-aberta:
            # erro aqui nao quebra envio nem marca notificacao como falha.
            await record_sent(
                session,
                wamid=extract_wamid(send_result),
                template_name=spec.name,
                recipient_jid=cliente.whatsapp,
            )
        else:
            text = render_message(notificacao, nome_full)
            await adapter.send_text(cliente.whatsapp, text)
    except WhatsAppError as e:
        log.warning("notify.send_failed", notif_id=str(notificacao.id), error=str(e))
        await repo.mark_failed(notificacao)
        return False

    await repo.mark_sent(notificacao)
    log.info("notify.sent", notif_id=str(notificacao.id), tipo=notificacao.tipo.value)

    # Acha a conversa ativa do cliente (se houver) pra: (1) gravar a mensagem no
    # historico da dashboard e (2) preparar o follow-up de CSAT no OS_CONCLUIDA.
    conversa = await ConversaRepo(session).find_active_by_cliente_id(cliente.id)

    if conversa is not None:
        # Persiste o texto legivel na conversa — antes a notificacao ia direto pro
        # WhatsApp sem gravar e sumia do historico da dashboard. Best-effort:
        # falha aqui nao quebra o envio (mensagem ja foi entregue).
        try:
            from ondeline_api.repositories.mensagem import MensagemRepo
            await MensagemRepo(session).insert_bot_reply(
                conversa_id=conversa.id,
                text=render_message(notificacao, nome_full),
            )
        except Exception:
            log.warning("notify.persist_failed", notif_id=str(notificacao.id), exc_info=True)

    # OS_CONCLUIDA: prepara a conversa pra capturar CSAT na proxima resposta do cliente.
    # Sem isso, o FSM nao sabe que estamos aguardando avaliacao e roteia pro LLM.
    if notificacao.tipo is NotificacaoTipo.OS_CONCLUIDA and conversa is not None:
        os_id_raw = (notificacao.payload or {}).get("os_id")
        if os_id_raw:
            try:
                conversa.followup_os_id = UUID(str(os_id_raw))
            except ValueError:
                log.warning("notify.os_concluida.bad_os_id", os_id=str(os_id_raw))
            else:
                conversa.estado = ConversaEstado.AGUARDA_FOLLOWUP_OS
                await session.flush()
                log.info(
                    "notify.os_concluida.state_set",
                    conversa_id=str(conversa.id),
                    os_id=str(os_id_raw),
                )
    return True
