# apps/api/src/ondeline_api/services/segmento.py
"""Resolver de segmento de clientes — peça única p/ preview, export e disparo.

Aplica sempre os invariantes de elegibilidade (não-deletado, sem opt-out de
marketing, com WhatsApp) + filtros opcionais (cidade, status, plano).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente


def resolver_segmento(filtros: dict[str, Any]) -> Select[tuple[Cliente]]:
    """Monta o SELECT base de clientes elegíveis para o segmento."""
    stmt = select(Cliente).where(
        Cliente.deleted_at.is_(None),
        Cliente.marketing_optout.is_(False),
        Cliente.whatsapp != "",
    )
    cidade = (filtros.get("cidade") or "").strip()
    status = (filtros.get("status") or "").strip()
    plano = (filtros.get("plano") or "").strip()
    if cidade:
        stmt = stmt.where(Cliente.cidade == cidade)
    if status:
        stmt = stmt.where(Cliente.status == status)
    if plano:
        stmt = stmt.where(Cliente.plano == plano)
    return stmt


async def contar_segmento(session: AsyncSession, filtros: dict[str, Any]) -> int:
    base = resolver_segmento(filtros).subquery()
    total = (await session.execute(select(func.count()).select_from(base))).scalar_one()
    return int(total)


async def amostra_segmento(
    session: AsyncSession, filtros: dict[str, Any], *, limite: int = 10
) -> list[dict[str, Any]]:
    stmt = resolver_segmento(filtros).order_by(Cliente.created_at.desc()).limit(limite)
    rows = list((await session.execute(stmt)).scalars().all())
    out: list[dict[str, Any]] = []
    for c in rows:
        try:
            nome = decrypt_pii(c.nome_encrypted) if c.nome_encrypted else None
        except Exception:
            nome = None
        out.append(
            {"id": str(c.id), "nome": nome, "whatsapp": c.whatsapp, "cidade": c.cidade}
        )
    return out


async def valores_distintos(session: AsyncSession) -> dict[str, list[str]]:
    """Valores distintos de cidade/status/plano na base (clientes vivos)."""
    out: dict[str, list[str]] = {}
    for chave, coluna in (
        ("cidades", Cliente.cidade),
        ("status", Cliente.status),
        ("planos", Cliente.plano),
    ):
        stmt = (
            select(coluna)
            .where(Cliente.deleted_at.is_(None), coluna.is_not(None), coluna != "")
            .distinct()
            .order_by(coluna)
        )
        out[chave] = [v for (v,) in (await session.execute(stmt)).all() if v is not None]
    return out
