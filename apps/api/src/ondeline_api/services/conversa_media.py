"""Storage + download de midia de conversas (foto/audio/video/doc do cliente).

Arquivos ficam em ``MEDIA_DIR/{conversa_id}/{mensagem_id}{ext}``. Em producao,
o volume nomeado ``conversa_media`` montado nesse path garante persistencia
entre deploys — sem ele, Watchtower recria o container e a midia some.

Fluxo inbound:
  1. ``inbound`` insere a Mensagem com ``media_type`` e seta ``media_url`` pra
     rota servivel ``/api/v1/conversas/{cid}/media/{mid}`` (URL estavel, nao
     corre contra o download async).
  2. ``baixar_midia_task`` (worker) chama ``download_and_store`` que baixa os
     bytes via adapter provider-aware (Evolution ou Cloud) e salva em disco.
  3. A rota GET serve o arquivo; se ainda nao chegou, tenta on-demand.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Mensagem

log = structlog.get_logger(__name__)

# Mesmo path usado pelo endpoint de envio do atendente (conversas.py:_MEDIA_DIR).
MEDIA_DIR = Path("/tmp/ondeline_conversa_media")

# WhatsApp manda mimes que o mimetypes da stdlib mapeia mal (ou nada).
_EXT_OVERRIDE = {
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/amr": ".amr",
    "audio/wav": ".wav",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/3gpp": ".3gp",
    "application/pdf": ".pdf",
}


def ext_for_mime(mime: str) -> str:
    """Resolve extensao de arquivo a partir do mime (com codecs, ex 'audio/ogg; codecs=opus')."""
    base = (mime or "").split(";")[0].strip().lower()
    if base in _EXT_OVERRIDE:
        return _EXT_OVERRIDE[base]
    guessed = mimetypes.guess_extension(base) if base else None
    return guessed or ".bin"


def conversa_dir(conversa_id: UUID) -> Path:
    return MEDIA_DIR / str(conversa_id)


def find_media_file(conversa_id: UUID, mensagem_id: UUID) -> Path | None:
    """Procura o arquivo ``{mensagem_id}.*`` no diretorio da conversa."""
    d = conversa_dir(conversa_id)
    if not d.is_dir():
        return None
    return next((p for p in d.glob(f"{mensagem_id}.*") if p.is_file()), None)


def store_bytes(conversa_id: UUID, mensagem_id: UUID, data: bytes, mime: str) -> Path:
    """Salva bytes em disco como ``{mensagem_id}{ext}`` (0600). Idempotente por nome."""
    d = conversa_dir(conversa_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{mensagem_id}{ext_for_mime(mime)}"
    path.write_bytes(data)
    path.chmod(0o600)
    return path


async def download_and_store(
    session: AsyncSession,
    mensagem_id: UUID,
    *,
    message_key: dict[str, Any] | None,
    settings: Any,
) -> Path | None:
    """Baixa a midia inbound via adapter provider-aware e persiste em disco.

    Idempotente: se ja existe arquivo pra essa mensagem, devolve sem rebaixar.
    Retorna o ``Path`` salvo ou ``None`` em falha (logada, nao propaga).
    """
    m = (
        await session.execute(select(Mensagem).where(Mensagem.id == mensagem_id))
    ).scalar_one_or_none()
    if m is None:
        log.warning("conversa_media.mensagem_not_found", mensagem_id=str(mensagem_id))
        return None

    existing = find_media_file(m.conversa_id, mensagem_id)
    if existing is not None:
        return existing

    # Provider-aware: Evolution OU Cloud conforme canal da conversa.
    from ondeline_api.services.canal_whatsapp import adapter_for_conversa

    adapter = await adapter_for_conversa(session, m.conversa_id, settings)
    try:
        key = message_key or {"id": m.external_id}
        data, mime = await adapter.get_media_base64(message_key=key)
    except Exception as e:  # WhatsAppError, expiracao de URL Cloud, etc.
        log.warning(
            "conversa_media.download_failed",
            mensagem_id=str(mensagem_id),
            error=str(e),
        )
        return None
    finally:
        await adapter.aclose()

    path = store_bytes(m.conversa_id, mensagem_id, data, mime)
    log.info(
        "conversa_media.stored",
        mensagem_id=str(mensagem_id),
        bytes=len(data),
        mime=mime,
    )
    return path
