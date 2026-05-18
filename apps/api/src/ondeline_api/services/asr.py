"""F7 — Orquestrador de transcrição de áudio (OpenAI Whisper).

Fluxo:
  1. Carrega ``Mensagem`` (audio) pelo id.
  2. Pede o binário pra Evolution via ``get_media_base64`` (a partir da key).
  3. Envia pra OpenAI Whisper API.
  4. Persiste ``transcricao_encrypted`` (Fernet) + ``transcricao_status``.
  5. Tambem espelha em ``content_encrypted`` se ainda nao houver — isso permite
     que o LLM ``run_turn`` veja a transcricao no historico como se fosse texto.
  6. Devolve a transcricao.

Falhas (HTTP, vazio, audio nao recuperavel) marcam status=failed e devolvem None.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.asr.openai_whisper import AsrError, OpenAiWhisperClient
from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.business import Mensagem
from ondeline_api.observability.metrics import (
    asr_audio_total,
    asr_failure_total,
)

log = structlog.get_logger(__name__)


async def transcrever_mensagem(
    session: AsyncSession,
    mensagem_id: UUID,
    *,
    asr: OpenAiWhisperClient,
    evolution: EvolutionAdapter,
    external_message_key: dict[str, object] | None = None,
) -> str | None:
    """Transcreve o audio da Mensagem e persiste. Devolve texto ou None."""
    m = (
        await session.execute(select(Mensagem).where(Mensagem.id == mensagem_id))
    ).scalar_one_or_none()
    if m is None:
        log.warning("asr.mensagem_not_found", mensagem_id=str(mensagem_id))
        return None
    if m.media_type != "audio":
        log.warning(
            "asr.not_audio",
            mensagem_id=str(mensagem_id),
            media_type=m.media_type,
        )
        return None

    # Recupera o binario via Evolution.
    key: dict[str, object] = external_message_key or {"id": m.external_id}
    try:
        audio_bytes, mime = await evolution.get_media_base64(message_key=key)
    except EvolutionError as e:
        log.warning("asr.evolution_fetch_failed", error=str(e))
        m.transcricao_status = "failed"
        await session.flush()
        asr_failure_total.labels(motivo="evolution").inc()
        return None

    # Chama OpenAI.
    try:
        text = await asr.transcrever(
            audio_bytes=audio_bytes, filename="audio.ogg", mime=mime
        )
    except AsrError as e:
        log.warning("asr.openai_failed", error=str(e))
        m.transcricao_status = "failed"
        await session.flush()
        asr_failure_total.labels(motivo="openai").inc()
        return None

    # Persiste — transcricao_encrypted sempre, content_encrypted so se vazio
    # (pra que o LLM enxergue como mensagem de texto).
    text_enc = encrypt_pii(text)
    m.transcricao_encrypted = text_enc
    m.transcricao_status = "ok"
    if m.content_encrypted is None:
        m.content_encrypted = text_enc
    await session.flush()
    asr_audio_total.inc()
    log.info(
        "asr.done",
        mensagem_id=str(mensagem_id),
        chars=len(text),
        bytes=len(audio_bytes),
    )
    return text


async def marcar_skipped(
    session: AsyncSession, mensagem_id: UUID, motivo: str
) -> None:
    """Marca mensagem como skipped (ex: audio > limite, ou OpenAI desabilitado)."""
    m = (
        await session.execute(select(Mensagem).where(Mensagem.id == mensagem_id))
    ).scalar_one_or_none()
    if m is None:
        return
    m.transcricao_status = "skipped"
    await session.flush()
    asr_failure_total.labels(motivo=motivo).inc()
