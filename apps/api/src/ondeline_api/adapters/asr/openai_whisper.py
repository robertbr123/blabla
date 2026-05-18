"""F7 — Cliente OpenAI Whisper API.

POST multipart pra ``https://api.openai.com/v1/audio/transcriptions`` com
``model=whisper-1`` e ``language=pt``. Trata erros transientes com 1 retry.

LGPD: o audio sai da infra. Aviso ao cliente eh tratado em outra camada
(services/asr.py + services/inbound.py).
"""
from __future__ import annotations

import asyncio

import httpx
import structlog

log = structlog.get_logger(__name__)


class AsrError(RuntimeError):
    """Falha definitiva na transcrição."""


class OpenAiWhisperClient:
    def __init__(
        self,
        *,
        api_key: str,
        url: str,
        model: str,
        language: str,
        timeout: float = 30.0,
        max_bytes: int = 25 * 1024 * 1024,
    ) -> None:
        self._api_key = api_key
        self._url = url
        self._model = model
        self._language = language
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def transcrever(
        self,
        *,
        audio_bytes: bytes,
        filename: str = "audio.ogg",
        mime: str = "audio/ogg",
    ) -> str:
        """Devolve texto transcrito. Levanta ``AsrError`` em falha definitiva."""
        if not self._api_key:
            raise AsrError("OPENAI_API_KEY nao configurado")
        if len(audio_bytes) == 0:
            raise AsrError("audio vazio")
        if len(audio_bytes) > self._max_bytes:
            raise AsrError(
                f"audio excede limite OpenAI: {len(audio_bytes)} > {self._max_bytes} bytes"
            )

        headers = {"Authorization": f"Bearer {self._api_key}"}
        files = {"file": (filename, audio_bytes, mime)}
        data = {
            "model": self._model,
            "language": self._language,
            "response_format": "json",
        }

        last_exc: Exception | None = None
        for attempt in range(2):  # 1 try + 1 retry
            try:
                resp = await self._client.post(
                    self._url, headers=headers, files=files, data=data
                )
                if 200 <= resp.status_code < 300:
                    try:
                        payload = resp.json()
                    except Exception as e:
                        raise AsrError(f"resposta invalida: {e}") from e
                    text = (payload.get("text") or "").strip()
                    if not text:
                        raise AsrError("transcricao vazia")
                    return text
                if resp.status_code >= 500 and attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                raise AsrError(
                    f"openai_whisper HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                raise AsrError(f"openai_whisper rede: {type(e).__name__}: {e}") from e
        raise AsrError(f"openai_whisper esgotou retries: {last_exc}")
