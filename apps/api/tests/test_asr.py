"""F7 — Transcrição de áudio via OpenAI Whisper."""
from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from ondeline_api.adapters.asr.openai_whisper import AsrError, OpenAiWhisperClient

pytestmark = pytest.mark.asyncio


async def test_transcrever_sucesso() -> None:
    async with respx.mock(assert_all_called=False) as router:
        router.post("https://api.openai.com/v1/audio/transcriptions").respond(
            200, json={"text": "olá, tô sem internet"}
        )
        cli = OpenAiWhisperClient(
            api_key="sk-test",
            url="https://api.openai.com/v1/audio/transcriptions",
            model="whisper-1",
            language="pt",
        )
        try:
            out = await cli.transcrever(audio_bytes=b"fakebytes")
        finally:
            await cli.aclose()
    assert out == "olá, tô sem internet"


async def test_transcrever_sem_api_key_falha() -> None:
    cli = OpenAiWhisperClient(
        api_key="",
        url="https://api.openai.com/v1/audio/transcriptions",
        model="whisper-1",
        language="pt",
    )
    try:
        with pytest.raises(AsrError, match="OPENAI_API_KEY"):
            await cli.transcrever(audio_bytes=b"x")
    finally:
        await cli.aclose()


async def test_transcrever_audio_vazio_falha() -> None:
    cli = OpenAiWhisperClient(
        api_key="sk-x",
        url="https://api.openai.com/v1/audio/transcriptions",
        model="whisper-1",
        language="pt",
    )
    try:
        with pytest.raises(AsrError, match="vazio"):
            await cli.transcrever(audio_bytes=b"")
    finally:
        await cli.aclose()


async def test_transcrever_audio_grande_falha() -> None:
    cli = OpenAiWhisperClient(
        api_key="sk-x",
        url="https://api.openai.com/v1/audio/transcriptions",
        model="whisper-1",
        language="pt",
        max_bytes=10,
    )
    try:
        with pytest.raises(AsrError, match="excede limite"):
            await cli.transcrever(audio_bytes=b"x" * 11)
    finally:
        await cli.aclose()


async def test_transcrever_500_retry_e_sucesso() -> None:
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(
            "https://api.openai.com/v1/audio/transcriptions"
        ).mock(
            side_effect=[
                httpx.Response(500, text="server err"),
                httpx.Response(200, json={"text": "ok funcionou"}),
            ]
        )
        cli = OpenAiWhisperClient(
            api_key="sk",
            url="https://api.openai.com/v1/audio/transcriptions",
            model="whisper-1",
            language="pt",
        )
        try:
            out = await cli.transcrever(audio_bytes=b"x")
        finally:
            await cli.aclose()
    assert out == "ok funcionou"
    assert route.call_count == 2


async def test_transcrever_400_nao_retry() -> None:
    async with respx.mock(assert_all_called=False) as router:
        route = router.post(
            "https://api.openai.com/v1/audio/transcriptions"
        ).respond(400, text="bad")
        cli = OpenAiWhisperClient(
            api_key="sk",
            url="https://api.openai.com/v1/audio/transcriptions",
            model="whisper-1",
            language="pt",
        )
        try:
            with pytest.raises(AsrError, match="HTTP 400"):
                await cli.transcrever(audio_bytes=b"x")
        finally:
            await cli.aclose()
    assert route.call_count == 1


async def test_transcrever_resposta_vazia_falha() -> None:
    async with respx.mock(assert_all_called=False) as router:
        router.post(
            "https://api.openai.com/v1/audio/transcriptions"
        ).respond(200, json={"text": "  "})
        cli = OpenAiWhisperClient(
            api_key="sk",
            url="https://api.openai.com/v1/audio/transcriptions",
            model="whisper-1",
            language="pt",
        )
        try:
            with pytest.raises(AsrError, match="vazia"):
                await cli.transcrever(audio_bytes=b"x")
        finally:
            await cli.aclose()


# ── Integração com service ────────────────────────────────


async def test_service_transcrever_mensagem_persiste(db_session) -> None:
    """Garante que `transcrever_mensagem` persiste transcricao + atualiza content."""
    from unittest.mock import AsyncMock

    from ondeline_api.db.crypto import decrypt_pii
    from ondeline_api.repositories.conversa import ConversaRepo
    from ondeline_api.repositories.mensagem import MensagemRepo
    from ondeline_api.services.asr import transcrever_mensagem

    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp(
        "5511asr@s.whatsapp.net"
    )
    # Insere mensagem de audio (content vazio, media_type=audio).
    m = await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id="WAEVT_AUDIO_1",
        text=None,
        media_type="audio",
        media_url=None,
    )
    assert m is not None

    fake_asr: Any = AsyncMock()
    fake_asr.transcrever.return_value = "tô sem internet"
    fake_evo: Any = AsyncMock()
    fake_evo.get_media_base64.return_value = (b"audio bytes", "audio/ogg")

    out = await transcrever_mensagem(
        db_session, m.id, asr=fake_asr, evolution=fake_evo
    )
    assert out == "tô sem internet"

    await db_session.refresh(m)
    assert m.transcricao_status == "ok"
    assert m.transcricao_encrypted is not None
    assert decrypt_pii(m.transcricao_encrypted) == "tô sem internet"
    # content_encrypted tambem deve ter sido preenchido (espelho).
    assert m.content_encrypted is not None
    assert decrypt_pii(m.content_encrypted) == "tô sem internet"


async def test_service_falha_openai_marca_failed(db_session) -> None:
    from unittest.mock import AsyncMock

    from ondeline_api.adapters.asr.openai_whisper import AsrError
    from ondeline_api.repositories.conversa import ConversaRepo
    from ondeline_api.repositories.mensagem import MensagemRepo
    from ondeline_api.services.asr import transcrever_mensagem

    conv = await ConversaRepo(db_session).get_or_create_by_whatsapp(
        "5511asr_fail@s.whatsapp.net"
    )
    m = await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id="WAEVT_AUDIO_FAIL",
        text=None,
        media_type="audio",
        media_url=None,
    )
    assert m is not None

    fake_asr: Any = AsyncMock()
    fake_asr.transcrever.side_effect = AsrError("openai 503")
    fake_evo: Any = AsyncMock()
    fake_evo.get_media_base64.return_value = (b"x", "audio/ogg")

    out = await transcrever_mensagem(
        db_session, m.id, asr=fake_asr, evolution=fake_evo
    )
    assert out is None
    await db_session.refresh(m)
    assert m.transcricao_status == "failed"
    assert m.transcricao_encrypted is None
    assert m.content_encrypted is None
