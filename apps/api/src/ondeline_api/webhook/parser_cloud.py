"""Parser do webhook da WhatsApp Cloud API (Meta).

Estrutura tipica do payload:

    {
      "object": "whatsapp_business_account",
      "entry": [{
        "id": "<WABA_ID>",
        "changes": [{
          "field": "messages",
          "value": {
            "metadata": {"phone_number_id": "<PHONE_ID>", ...},
            "contacts": [{"profile": {"name": "..."}, "wa_id": "5511..."}],
            "messages": [{
              "from": "5511...",
              "id": "wamid.HBgM...",
              "timestamp": "...",
              "type": "text|image|audio|video|document|sticker",
              "text": {"body": "..."}
              // ou: image: {"id": "media_id", "mime_type": "...", "caption": "..."}
              // ou: audio: {"id": "media_id", "mime_type": "audio/ogg; codecs=opus", "voice": true}
              // ...
            }]
          }
        }]
      }]
    }

Tambem ha eventos com ``statuses[]`` (delivered/read) em vez de ``messages[]``
— esses sao ignorados pelo parser (caller filtra antes ou recebe ParseError).

Produz o mesmo ``InboundEvent`` da Evolution, populando ``media_id`` e
``cloud_phone_id`` quando aplicaveis.
"""
from __future__ import annotations

from typing import Any

from ondeline_api.webhook.parser import InboundEvent, InboundKind, ParseError

_TYPE_MAP: dict[str, InboundKind] = {
    "text": InboundKind.TEXT,
    "image": InboundKind.IMAGE,
    "audio": InboundKind.AUDIO,
    "video": InboundKind.VIDEO,
    "document": InboundKind.DOCUMENT,
    "sticker": InboundKind.STICKER,
}


def iter_cloud_statuses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Itera por todos os status updates (delivered/read/failed/sent) do payload.

    Status updates vem em ``entry[].changes[].value.statuses[]`` quando o Meta
    notifica sobre o ciclo de vida de uma mensagem outbound:

    - ``sent``: Meta aceitou e ta encaminhando
    - ``delivered``: chegou no celular do destinatario
    - ``read``: cliente abriu a conversa
    - ``failed``: falha de entrega (com codigo de erro em ``errors[]``)

    Retorna lista de dicts achatados pra facilitar logging:
        {"id": "wamid....", "status": "delivered", "timestamp": "...",
         "recipient_id": "5511...", "errors": [...] | None}
    """
    out: list[dict[str, Any]] = []
    if payload.get("object") != "whatsapp_business_account":
        return out
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            statuses = value.get("statuses") or []
            if not isinstance(statuses, list):
                continue
            for st in statuses:
                if not isinstance(st, dict):
                    continue
                out.append(
                    {
                        "id": str(st.get("id") or ""),
                        "status": str(st.get("status") or ""),
                        "timestamp": str(st.get("timestamp") or ""),
                        "recipient_id": str(st.get("recipient_id") or ""),
                        "errors": st.get("errors"),
                    }
                )
    return out


def parse_cloud_message(payload: dict[str, Any]) -> InboundEvent:
    """Extrai a primeira mensagem de um payload Cloud API.

    Webhooks da Meta podem trazer multiplas mensagens num payload, mas na
    pratica vem 1 — o caller deveria iterar se >1.
    Veja ``iter_cloud_messages`` pra obter todos.
    """
    msgs = list(iter_cloud_messages(payload))
    if not msgs:
        raise ParseError("no messages in payload")
    return msgs[0]


def iter_cloud_messages(payload: dict[str, Any]) -> list[InboundEvent]:
    """Itera por todas as mensagens em todos os ``changes`` do payload."""
    if payload.get("object") != "whatsapp_business_account":
        raise ParseError(
            f"unexpected object: {payload.get('object')!r}"
        )

    entries = payload.get("entry") or []
    if not isinstance(entries, list):
        raise ParseError("entry must be a list")

    out: list[InboundEvent] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue

            phone_number_id = str(
                (value.get("metadata") or {}).get("phone_number_id") or ""
            )

            # Mapa wa_id -> profile name (Meta as vezes manda 1 contact, as vezes 0)
            contacts = value.get("contacts") or []
            names: dict[str, str] = {}
            if isinstance(contacts, list):
                for c in contacts:
                    if not isinstance(c, dict):
                        continue
                    wa_id = str(c.get("wa_id") or "")
                    profile = c.get("profile") or {}
                    name = str((profile.get("name") if isinstance(profile, dict) else "") or "")
                    if wa_id and name:
                        names[wa_id] = name

            messages = value.get("messages") or []
            if not isinstance(messages, list):
                continue
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                evt = _parse_single_message(msg, names, phone_number_id)
                if evt is not None:
                    out.append(evt)
    return out


def _parse_single_message(
    msg: dict[str, Any],
    names: dict[str, str],
    phone_number_id: str,
) -> InboundEvent | None:
    """Converte 1 message Cloud em InboundEvent (None pra tipos nao suportados)."""
    external_id = msg.get("id")
    if not external_id:
        return None
    sender = str(msg.get("from") or "")
    msg_type = str(msg.get("type") or "")
    push_name = names.get(sender, "Cliente")

    kind = _TYPE_MAP.get(msg_type)
    if kind is None:
        # tipos exoticos (reaction, contacts, location, interactive button reply) — ignora por ora
        return None

    text: str | None = None
    media_id: str | None = None

    if kind is InboundKind.TEXT:
        body = (msg.get("text") or {}).get("body") or ""
        text = body.strip() or None
    elif kind is InboundKind.IMAGE:
        img = msg.get("image") or {}
        media_id = str(img.get("id") or "") or None
        caption = img.get("caption")
        if isinstance(caption, str):
            text = caption.strip() or None
    elif kind is InboundKind.AUDIO:
        aud = msg.get("audio") or {}
        media_id = str(aud.get("id") or "") or None
    elif kind is InboundKind.VIDEO:
        vid = msg.get("video") or {}
        media_id = str(vid.get("id") or "") or None
        caption = vid.get("caption")
        if isinstance(caption, str):
            text = caption.strip() or None
    elif kind is InboundKind.DOCUMENT:
        doc = msg.get("document") or {}
        media_id = str(doc.get("id") or "") or None
    elif kind is InboundKind.STICKER:
        stk = msg.get("sticker") or {}
        media_id = str(stk.get("id") or "") or None

    return InboundEvent(
        external_id=str(external_id),
        jid=sender,  # E.164 puro — codigo downstream que precise de sufixo deve adicionar
        push_name=push_name,
        kind=kind,
        text=text,
        from_me=False,  # Cloud API so manda inbound; status updates vem em outro evento
        instance="",
        media_id=media_id,
        cloud_phone_id=phone_number_id,
    )
