"""Cliente para WhatsApp Cloud API (Meta Graph API) — STUB.

Implementacao real chega no PR3. Este arquivo existe pra:
1. Fixar o shape da classe que sera usado pelo factory (`adapters.whatsapp.__init__`).
2. Permitir que testes e type-checking saibam que ``CloudAdapter`` cumpre o
   Protocol ``WhatsAppAdapter``.

Endpoint base: https://graph.facebook.com/{version}/{phone_number_id}/messages
Auth: Bearer token (system user ou long-lived access token).
Restricoes importantes (vs Evolution):
- Fora da janela de 24h do cliente, so da pra mandar TEMPLATE pre-aprovado.
- Media outbound: pode ser URL publica ou upload previo (media_id).
- Media inbound: webhook traz ``media_id`` — precisa GET autenticado pra baixar.
"""
from __future__ import annotations

from typing import Any

import httpx

from ondeline_api.adapters.whatsapp.base import WhatsAppError


class CloudError(WhatsAppError):
    """Falha definitiva ao se comunicar com a Cloud API do Meta."""


class CloudAdapter:
    """STUB — todos os metodos levantam ``NotImplementedError`` por enquanto.

    Sera implementado no PR3 (Cloud API real). O shape ja respeita o Protocol
    ``WhatsAppAdapter`` pra o factory funcionar sem branches especiais.
    """

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        graph_version: str = "v21.0",
        timeout: float = 15.0,
        retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self._token = access_token
        self._phone_id = phone_number_id
        self._base = f"https://graph.facebook.com/{graph_version}"
        self._retries = retries
        self._backoff = backoff_seconds
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send_text(self, jid: str, text: str) -> dict[str, Any]:
        raise NotImplementedError("CloudAdapter.send_text — PR3")

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
        raise NotImplementedError("CloudAdapter.send_media — PR3")

    async def send_media_bytes(
        self,
        jid: str,
        *,
        data: bytes,
        mediatype: str,
        mimetype: str,
        file_name: str,
        caption: str = "",
    ) -> dict[str, Any]:
        raise NotImplementedError("CloudAdapter.send_media_bytes — PR3")

    async def get_media_base64(
        self, *, message_key: dict[str, Any], convert_to_mp4: bool = False
    ) -> tuple[bytes, str]:
        raise NotImplementedError("CloudAdapter.get_media_base64 — PR3")
