# apps/api/src/ondeline_api/services/whatsapp_templates_sync.py
"""Sincronização de templates do WhatsApp Cloud (Graph API) → broadcast_templates.

Puxa os templates APPROVED dos canais Cloud ATIVOS e faz upsert por nome.
"""
from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp.cloud import CloudAdapter
from ondeline_api.config import Settings
from ondeline_api.db.models.business import BroadcastTemplate, Canal

log = structlog.get_logger(__name__)

_VAR_RE = re.compile(r"{{(\d+)}}")
_BTN_TIPO = {"url": "url", "quick_reply": "quick_reply", "phone_number": "phone"}


def parse_meta_template(meta: dict[str, Any]) -> dict[str, Any]:
    """Converte um template da Graph API na estrutura do broadcast_templates."""
    variaveis: list[dict[str, Any]] = []
    header_tipo = "none"
    botoes: list[dict[str, Any]] = []
    for comp in meta.get("components") or []:
        ctype = (comp.get("type") or "").upper()
        if ctype == "BODY":
            n = len({int(m) for m in _VAR_RE.findall(comp.get("text") or "")})
            variaveis = [
                {"indice": i, "label": f"Variável {i}", "tipo": "texto"}
                for i in range(1, n + 1)
            ]
        elif ctype == "HEADER":
            header_tipo = "image" if (comp.get("format") or "").upper() == "IMAGE" else "none"
        elif ctype == "BUTTONS":
            for idx, b in enumerate(comp.get("buttons") or []):
                url = b.get("url") or ""
                botoes.append(
                    {
                        "index": idx,
                        "tipo": _BTN_TIPO.get((b.get("type") or "").lower(), (b.get("type") or "").lower()),
                        "texto": b.get("text") or "",
                        "url_dinamica": "{{" in url,
                    }
                )
    return {
        "name": meta["name"],
        "language": meta.get("language") or "pt_BR",
        "category": meta.get("category") or "MARKETING",
        "variaveis": variaveis,
        "header_tipo": header_tipo,
        "botoes": botoes,
    }


async def upsert_template(session: AsyncSession, spec: dict[str, Any]) -> None:
    """Insere ou atualiza um broadcast_template por nome."""
    existing = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == spec["name"])
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            BroadcastTemplate(
                name=spec["name"],
                language=spec["language"],
                category=spec["category"],
                variaveis=spec["variaveis"],
                header_tipo=spec["header_tipo"],
                botoes=spec["botoes"],
                ativo=True,
            )
        )
    else:
        existing.language = spec["language"]
        existing.category = spec["category"]
        existing.variaveis = spec["variaveis"]
        existing.header_tipo = spec["header_tipo"]
        existing.botoes = spec["botoes"]
        existing.ativo = True


async def sincronizar_templates(session: AsyncSession, settings: Settings) -> dict[str, int]:
    """Sincroniza templates APPROVED dos canais Cloud ativos."""
    canais = list(
        (
            await session.execute(
                select(Canal).where(Canal.provider == "cloud", Canal.ativo.is_(True))
            )
        )
        .scalars()
        .all()
    )
    sincronizados = 0
    for canal in canais:
        if not canal.cloud_waba_id:
            continue
        adapter = CloudAdapter(
            access_token=settings.whatsapp_cloud_access_token,
            phone_number_id=canal.cloud_phone_id or "",
            graph_version=settings.whatsapp_cloud_graph_version,
        )
        try:
            data = await adapter.list_message_templates(canal.cloud_waba_id)
        finally:
            await adapter.aclose()
        for meta in data.get("data") or []:
            if (meta.get("status") or "").upper() != "APPROVED":
                continue
            await upsert_template(session, parse_meta_template(meta))
            sincronizados += 1
    await session.commit()
    return {"sincronizados": sincronizados, "canais": len(canais)}
