# apps/api/tests/test_templates_sync.py
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from ondeline_api.db.models.business import BroadcastTemplate
from ondeline_api.services.whatsapp_templates_sync import (
    parse_meta_template,
    upsert_template,
)


def test_parse_body_vars_header_e_botoes() -> None:
    meta = {
        "name": "promo_x",
        "language": "pt_BR",
        "category": "MARKETING",
        "status": "APPROVED",
        "components": [
            {"type": "HEADER", "format": "IMAGE"},
            {"type": "BODY", "text": "Oi {{1}}, veja {{2}}"},
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "URL", "text": "Abrir", "url": "https://x.com/{{1}}"},
                    {"type": "QUICK_REPLY", "text": "Parar"},
                ],
            },
        ],
    }
    out = parse_meta_template(meta)
    assert out["name"] == "promo_x"
    assert out["header_tipo"] == "image"
    assert len(out["variaveis"]) == 2
    assert out["variaveis"][0] == {"indice": 1, "label": "Variável 1", "tipo": "texto"}
    assert out["botoes"][0] == {
        "index": 0, "tipo": "url", "texto": "Abrir", "url_dinamica": True,
    }
    assert out["botoes"][1]["tipo"] == "quick_reply"
    assert out["botoes"][1]["url_dinamica"] is False


def test_parse_sem_componentes() -> None:
    out = parse_meta_template({"name": "x", "language": "pt_BR", "components": []})
    assert out["variaveis"] == []
    assert out["header_tipo"] == "none"
    assert out["botoes"] == []


@pytest.mark.asyncio
async def test_upsert_idempotente(db_session) -> None:
    nome = "tpl_" + uuid.uuid4().hex[:8]
    spec = {"name": nome, "language": "pt_BR", "category": "MARKETING",
            "variaveis": [], "header_tipo": "none", "botoes": []}
    await upsert_template(db_session, spec)
    await upsert_template(db_session, {**spec, "header_tipo": "image"})
    await db_session.flush()
    rows = list((await db_session.execute(
        select(BroadcastTemplate).where(BroadcastTemplate.name == nome)
    )).scalars().all())
    assert len(rows) == 1
    assert rows[0].header_tipo == "image"
