"""Cliente para WhatsApp Cloud API (Meta Graph API).

Endpoints usados:
- POST /{phone_number_id}/messages          envia text/media/template
- POST /{phone_number_id}/media             upload bytes -> media_id
- GET  /{media_id}                          retorna URL de download (5min TTL)
- GET  {url do passo anterior}              baixa o binario (autenticado)

Diferencas vs Evolution:
- ``jid`` aqui e numero E.164 puro (ex: ``5511999999999``). Aceitamos o formato
  Evolution (``5511...@s.whatsapp.net``) e fazemos strip do sufixo pra compat
  com codigo legado.
- ``send_media_bytes`` faz 2 chamadas (upload + send).
- ``get_media_base64`` espera ``message_key={"media_id": "..."}`` (Cloud) em vez
  do dict da Evolution. Ambos cumprem o Protocol — caller passa o dict certo.
- Fora da janela de 24h so da pra mandar TEMPLATE (``send_template``).
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from ondeline_api.adapters.whatsapp.base import WhatsAppError

log = structlog.get_logger(__name__)


class CloudError(WhatsAppError):
    """Falha definitiva ao se comunicar com a Cloud API do Meta."""


def _strip_jid_suffix(jid: str) -> str:
    """Aceita 5511...@s.whatsapp.net ou 5511... e devolve so o E.164."""
    if "@" in jid:
        return jid.split("@", 1)[0]
    return jid


class CloudAdapter:
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

    async def list_message_templates(self, waba_id: str) -> dict[str, Any]:
        """Lista os message templates de um WABA (Graph API).

        Retorna o JSON cru: ``{"data": [ {name, status, language, category,
        components}, ... ]}``.
        """
        path = (
            f"/{waba_id}/message_templates"
            "?fields=name,status,language,category,components&limit=200"
        )
        return await self._get_json(path)

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── public ────────────────────────────────────────────────

    async def send_text(self, jid: str, text: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": _strip_jid_suffix(jid),
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }
        return await self._post_json(f"/{self._phone_id}/messages", payload)

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
        """Envia media por URL publica. Meta busca o arquivo direto da URL.

        ``mediatype`` aceita: image | audio | video | document | sticker.
        Note que ``audio`` e ``sticker`` nao aceitam caption no Cloud API.
        """
        body: dict[str, Any] = {"link": url}
        if mediatype in ("image", "video", "document"):
            if caption:
                body["caption"] = caption
        if mediatype == "document" and file_name:
            body["filename"] = file_name

        payload = {
            "messaging_product": "whatsapp",
            "to": _strip_jid_suffix(jid),
            "type": mediatype,
            mediatype: body,
        }
        return await self._post_json(f"/{self._phone_id}/messages", payload)

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
        """Upload do binario (-> media_id) + send (-> message_id).

        Mais lento que ``send_media`` (2 round-trips) mas necessario quando o
        binario e gerado on-the-fly (QR Pix, boleto PDF) e nao tem URL publica.
        """
        # 1) Upload
        files = {
            "file": (file_name, data, mimetype),
            "messaging_product": (None, "whatsapp"),
            "type": (None, mimetype),
        }
        upload = await self._post_multipart(f"/{self._phone_id}/media", files)
        media_id = upload.get("id")
        if not media_id:
            raise CloudError(f"upload sem id: {upload}")

        # 2) Send referenciando o media_id
        body: dict[str, Any] = {"id": str(media_id)}
        if mediatype in ("image", "video", "document") and caption:
            body["caption"] = caption
        if mediatype == "document" and file_name:
            body["filename"] = file_name
        payload = {
            "messaging_product": "whatsapp",
            "to": _strip_jid_suffix(jid),
            "type": mediatype,
            mediatype: body,
        }
        return await self._post_json(f"/{self._phone_id}/messages", payload)

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
    ) -> dict[str, Any]:
        """Envia mensagem TEMPLATE (unica forma fora da janela 24h).

        ``body_params`` ordem segue {{1}}, {{2}}, ... do template.
        ``header_media_url`` so usado se o template tem header com media.
        ``otp_code`` so para templates de AUTENTICACAO com botao copiar-codigo:
        o Meta exige o codigo tambem no componente ``button`` (sub_type=url,
        index=0), alem de estar no body. Veja docs de authentication templates.
        """
        components: list[dict[str, Any]] = []
        if header_media_url and header_media_type:
            components.append(
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": header_media_type,
                            header_media_type: {"link": header_media_url},
                        }
                    ],
                }
            )
        if body_params:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in body_params],
                }
            )
        if otp_code is not None:
            # Botao do template de autenticacao (copiar codigo / one-tap).
            # Meta usa sub_type='url' e exige o codigo repetido aqui.
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": 0,
                    "parameters": [{"type": "text", "text": otp_code}],
                }
            )
        if button_url_param is not None:
            # Botão URL dinâmico (índice 0). Botão estático não precisa de componente.
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": 0,
                    "parameters": [{"type": "text", "text": button_url_param}],
                }
            )
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": _strip_jid_suffix(jid),
            "type": "template",
            "template": {
                "name": name,
                "language": {"code": language},
            },
        }
        if components:
            payload["template"]["components"] = components
        return await self._post_json(f"/{self._phone_id}/messages", payload)

    async def get_media_base64(
        self, *, message_key: dict[str, Any], convert_to_mp4: bool = False
    ) -> tuple[bytes, str]:
        """Baixa media inbound. ``message_key`` deve conter ``media_id``.

        2 passos: (1) GET /{media_id} -> retorna URL temp + mime_type;
        (2) GET nessa URL com Bearer pra pegar os bytes.
        ``convert_to_mp4`` e ignorado (Meta nao oferece conversao).
        """
        media_id = message_key.get("media_id") or message_key.get("id")
        if not media_id:
            raise CloudError("get_media_base64: message_key sem 'media_id'")

        meta = await self._get_json(f"/{media_id}")
        url = meta.get("url")
        mime = str(meta.get("mime_type") or "application/octet-stream")
        if not url:
            raise CloudError(f"media {media_id}: sem URL ({meta})")

        # Download autenticado (URL expira em 5min)
        resp = await self._client.get(
            url, headers={"Authorization": f"Bearer {self._token}"}
        )
        if resp.status_code != 200:
            raise CloudError(
                f"media download HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return resp.content, mime

    # ── internal ──────────────────────────────────────────────

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _post_json(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _get_json(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def _post_multipart(
        self, path: str, files: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        # multipart usa header Authorization mas SEM Content-Type fixo
        # (httpx calcula o boundary).
        headers = {"Authorization": f"Bearer {self._token}"}
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.post(url, files=files, headers=headers)
                if 200 <= resp.status_code < 300:
                    return resp.json() if resp.content else {}
                if resp.status_code >= 500 and attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise CloudError(
                    f"{path} -> HTTP {resp.status_code} body={resp.text[:300]}"
                )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise CloudError(f"{path} -> {type(e).__name__}: {e}") from e
        raise CloudError(f"{path} -> exhausted retries: {last_exc}")

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.request(
                    method, url, json=json, headers=self._headers
                )
                if 200 <= resp.status_code < 300:
                    return resp.json() if resp.content else {}
                if resp.status_code >= 500 and attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise CloudError(
                    f"{method} {path} -> HTTP {resp.status_code} body={resp.text[:300]}"
                )
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self._retries:
                    await asyncio.sleep(self._backoff * (attempt + 1))
                    continue
                raise CloudError(f"{method} {path} -> {type(e).__name__}: {e}") from e
        raise CloudError(f"{method} {path} -> exhausted retries: {last_exc}")
