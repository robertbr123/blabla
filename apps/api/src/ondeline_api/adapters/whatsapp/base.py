"""Protocol de adapter de WhatsApp — provider-agnostico.

Define o contrato que tanto a Evolution API (Baileys/n8n self-hosted) quanto a
Cloud API oficial do Meta devem cumprir. Toda chamada outbound (workers, tools,
services) deve depender deste Protocol, nao da implementacao concreta.

Tipos:
- ``WhatsAppAdapter``: Protocol async com send_text / send_media / get_media_bytes.
- ``WhatsAppError``: erro definitivo de envio (apos retries do adapter).
- ``SendResult``: dict cru devolvido pelo provider (ja ha codigo que le campos
  especificos da Evolution; manter ``dict[str, Any]`` evita migration grande).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

SendResult = dict[str, Any]


class WhatsAppError(RuntimeError):
    """Falha definitiva ao se comunicar com o provider de WhatsApp."""


@runtime_checkable
class WhatsAppAdapter(Protocol):
    async def send_text(self, jid: str, text: str) -> SendResult: ...

    async def send_media(
        self,
        jid: str,
        *,
        url: str,
        mediatype: str,
        mimetype: str,
        file_name: str,
        caption: str = "",
    ) -> SendResult: ...

    async def send_media_bytes(
        self,
        jid: str,
        *,
        data: bytes,
        mediatype: str,
        mimetype: str,
        file_name: str,
        caption: str = "",
    ) -> SendResult: ...

    async def send_template(
        self,
        jid: str,
        *,
        name: str,
        language: str = "pt_BR",
        body_params: list[str] | None = None,
        header_media_url: str | None = None,
        header_media_type: str | None = None,
        otp_code: str | None = None,
        button_url_param: str | None = None,
    ) -> SendResult: ...

    async def get_media_base64(
        self, *, message_key: dict[str, Any], convert_to_mp4: bool = False
    ) -> tuple[bytes, str]: ...

    async def aclose(self) -> None: ...
