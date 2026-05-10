"""Parser de payload Evolution `messages.upsert`.

Garante que extraimos: external_id (key.id), jid (remoteJid), fromMe, push_name,
texto / tipo de midia, e ignoramos eventos irrelevantes.
"""
from __future__ import annotations

from typing import Any

import pytest
from ondeline_api.webhook.parser import (
    InboundEvent,
    InboundKind,
    ParseError,
    parse_messages_upsert,
)


def _payload(text: str | None = "Oi", from_me: bool = False, **overrides: Any) -> dict[str, Any]:
    msg: dict[str, object] = {}
    if text is not None:
        msg["conversation"] = text
    base: dict[str, object] = {
        "event": "messages.upsert",
        "data": {
            "key": {"id": "ABC123", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": from_me},
            "pushName": "Maria",
            "message": msg,
        },
    }
    base.update(overrides)
    return base


def test_text_event_parsed() -> None:
    ev = parse_messages_upsert(_payload("Bom dia"))
    assert isinstance(ev, InboundEvent)
    assert ev.external_id == "ABC123"
    assert ev.jid == "5511999999999@s.whatsapp.net"
    assert ev.push_name == "Maria"
    assert ev.kind is InboundKind.TEXT
    assert ev.text == "Bom dia"
    assert ev.from_me is False


def test_extended_text_message_parsed() -> None:
    ev = parse_messages_upsert(
        _payload(text=None) | {
            "data": {
                "key": {"id": "X1", "remoteJid": "5511@s", "fromMe": False},
                "pushName": "P",
                "message": {"extendedTextMessage": {"text": "olá com link"}},
            }
        }
    )
    assert ev.text == "olá com link"


def test_from_me_marked() -> None:
    ev = parse_messages_upsert(_payload("eu", from_me=True))
    assert ev.from_me is True


def test_image_event() -> None:
    payload = _payload(text=None)
    payload["data"]["message"] = {"imageMessage": {"caption": "foto"}}
    ev = parse_messages_upsert(payload)
    assert ev.kind is InboundKind.IMAGE
    assert ev.text is None or ev.text == "foto"


def test_audio_event() -> None:
    payload = _payload(text=None)
    payload["data"]["message"] = {"audioMessage": {}}
    ev = parse_messages_upsert(payload)
    assert ev.kind is InboundKind.AUDIO


def test_document_event() -> None:
    payload = _payload(text=None)
    payload["data"]["message"] = {"documentMessage": {"fileName": "x.pdf"}}
    ev = parse_messages_upsert(payload)
    assert ev.kind is InboundKind.DOCUMENT


def test_sticker_event() -> None:
    payload = _payload(text=None)
    payload["data"]["message"] = {"stickerMessage": {}}
    ev = parse_messages_upsert(payload)
    assert ev.kind is InboundKind.STICKER


def test_unknown_event_raises() -> None:
    with pytest.raises(ParseError):
        parse_messages_upsert({"event": "presence.update", "data": {}})


def test_missing_data_raises() -> None:
    with pytest.raises(ParseError):
        parse_messages_upsert({"event": "messages.upsert"})


def test_missing_external_id_raises() -> None:
    with pytest.raises(ParseError):
        parse_messages_upsert(
            {"event": "messages.upsert", "data": {"key": {}, "message": {"conversation": "x"}}}
        )


def test_strips_whitespace_in_text() -> None:
    ev = parse_messages_upsert(_payload("   Oi mundo  \n"))
    assert ev.text == "Oi mundo"
