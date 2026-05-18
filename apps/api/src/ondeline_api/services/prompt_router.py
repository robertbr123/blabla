"""F5 — Roteador de variantes de prompt (A/B test).

Bucket determinístico: ``hash(whatsapp) % 100`` cai numa faixa de tráfego.
Variantes ativas (ordenadas por nome para reprodutibilidade) consomem faixas
sequenciais: a primeira ocupa [0, trafego_pct), a segunda [trafego_pct, t1+t2),
etc. O resto cai em 'default' (SYSTEM_PROMPT hardcoded — None devolvido aqui).

Mesma whatsapp sempre cai na mesma variante (consistência entre conversas).
Variantes podem ser filtradas por canal via ``canal_slug``.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import PromptVariant


def _bucket_for_jid(whatsapp: str) -> int:
    """0-99 deterministico por whatsapp. SHA256 -> primeiros 8 hex -> mod 100."""
    h = hashlib.sha256(whatsapp.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % 100


async def escolher_variante(
    session: AsyncSession, whatsapp: str, canal_slug: str | None = None
) -> PromptVariant | None:
    """Retorna a `PromptVariant` correspondente ao bucket, ou ``None`` se default.

    Ativas filtradas por canal (``canal_slug``) quando informado. Variantes
    sem ``canal_slug`` aplicam-se a todos os canais.
    """
    stmt = (
        select(PromptVariant)
        .where(PromptVariant.ativo.is_(True), PromptVariant.trafego_pct > 0)
        .order_by(PromptVariant.nome)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    # Filtra por canal: ou variante sem canal_slug (global) ou casando.
    aplicaveis = [
        v for v in rows
        if v.canal_slug is None or v.canal_slug == canal_slug
    ]
    if not aplicaveis:
        return None

    bucket = _bucket_for_jid(whatsapp)
    acc = 0
    for v in aplicaveis:
        acc += v.trafego_pct
        if bucket < acc:
            return v
    return None  # cai no default
