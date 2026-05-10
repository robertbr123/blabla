"""Parser do payload `messages.upsert` da Evolution API.

Reduz o JSON cru a um `InboundEvent` tipado e estavel. Tudo mais downstream
(FSM, services, tasks Celery) consome essa estrutura — nunca o dict cru.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class InboundKind(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"


class ParseError(ValueError):
    """Raised when the payload is not a valid messages.upsert event."""


@dataclass(frozen=True, slots=True)
class InboundEvent:
    external_id: str
    jid: str
    push_name: str
    kind: InboundKind
    text: str | None
    from_me: bool


def _truthy(v: Any) -> bool:
    return v in (True, "true", "True", 1, "1")


def parse_messages_upsert(payload: dict[str, Any]) -> InboundEvent:
    if payload.get("event") != "messages.upsert":
        raise ParseError(f"unsupported event: {payload.get('event')!r}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ParseError("missing data block")
    key = data.get("key") or {}
    external_id = key.get("id")
    if not external_id:
        raise ParseError("missing key.id")
    jid = key.get("remoteJid", "") or ""
    push_name = data.get("pushName", "Cliente") or "Cliente"
    msg = data.get("message") or {}

    if "stickerMessage" in msg:
        kind = InboundKind.STICKER
        text: str | None = None
    elif "audioMessage" in msg:
        kind = InboundKind.AUDIO
        text = None
    elif "imageMessage" in msg:
        kind = InboundKind.IMAGE
        text = (msg.get("imageMessage") or {}).get("caption")
        if isinstance(text, str):
            text = text.strip() or None
    elif "videoMessage" in msg:
        kind = InboundKind.VIDEO
        text = None
    elif "documentMessage" in msg:
        kind = InboundKind.DOCUMENT
        text = None
    else:
        raw = (
            msg.get("conversation")
            or (msg.get("extendedTextMessage") or {}).get("text")
            or ""
        )
        text = (raw or "").strip() or None
        kind = InboundKind.TEXT

    return InboundEvent(
        external_id=str(external_id),
        jid=jid,
        push_name=str(push_name),
        kind=kind,
        text=text,
        from_me=_truthy(key.get("fromMe")),
    )
