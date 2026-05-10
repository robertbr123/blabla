"""Cliente para Evolution API (WhatsApp).

Encapsula as chamadas HTTP para sendText / sendMedia, com timeout e retry simples
sobre falhas transientes (5xx ou ConnectError). Lanca `EvolutionError` em caso
de falha definitiva — o caller (worker) decide se re-enfileira via Celery retry.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class EvolutionError(RuntimeError):
    """Falha definitiva ao se comunicar com a Evolution API."""


class EvolutionAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        instance: str,
        api_key: str,
        timeout: float = 15.0,
        retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._instance = instance
        self._api_key = api_key
        self._retries = retries
        self._backoff = backoff_seconds
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── public ────────────────────────────────────────────────

    async def send_text(self, jid: str, text: str) -> dict[str, Any]:
        payload = {"number": jid, "text": text}
        return await self._post(f"/message/sendText/{self._instance}", payload)

    async def send_media(
        self,
        jid: str,
        *,
        url: str,
        mediatype: str,
        mimetype: str,
        file_name: str,
        caption: str = "",
    ) -> dict[str, Any]:
        payload = {
            "number": jid,
            "mediatype": mediatype,
            "mimetype": mimetype,
            "media": url,
            "fileName": file_name,
            "caption": caption,
        }
        return await self._post(f"/message/sendMedia/{self._instance}", payload)

    # ── internal ──────────────────────────────────────────────

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.post(
                    url,
                    json=json,
                    headers={"apikey": self._api_key, "Content-Type": "application/json"},
                )
                if 200 <= resp.status_code < 300:
                    return resp.json() if resp.content else {}
                if resp.status_code >= 500 and attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise EvolutionError(f"{path} -> HTTP {resp.status_code} body={resp.text[:200]}")
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise EvolutionError(f"{path} -> {type(e).__name__}: {e}") from e
        # caso defensivo — nunca deve cair aqui
        raise EvolutionError(f"{path} -> exhausted retries: {last_exc}")
