"""Logica das missoes (Fase 3d engajamento).

Catalogo hardcoded V1. Cada missao tem:
- titulo, descricao, pontos
- periodicidade: 'diaria' | 'por_os' | 'on_the_fly'
- gera_slug(extra) -> slug completo armazenado na tabela

Tres missoes V1:
- share_indicacao: 20 pts, 1x/dia max (slug=share_indicacao:YYYY-MM-DD)
- responder_nps:   50 pts, 1x por OS (slug=responder_nps:<os_id>)
- pagar_em_dia:    100 pts, calculado on-the-fly (1x por titulo SGP pago)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.cliente_app import (
    ClienteAppMissaoCompletada,
    ClienteAppUser,
)

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MissaoDef:
    slug_base: str
    titulo: str
    descricao: str
    pontos: int
    periodicidade: str  # 'diaria' | 'por_os' | 'on_the_fly'
    icon: str  # nome do icone do promo_icon_map.dart


MISSOES: dict[str, MissaoDef] = {
    "share_indicacao": MissaoDef(
        slug_base="share_indicacao",
        titulo="Compartilhe seu código",
        descricao="Mande seu código de indicação pelo WhatsApp ou status. +20 pts por dia.",
        pontos=20,
        periodicidade="diaria",
        icon="card_giftcard_rounded",
    ),
    "responder_nps": MissaoDef(
        slug_base="responder_nps",
        titulo="Avalie um atendimento",
        descricao="Responda a pesquisa de satisfacao ao final de um chamado. +50 pts por avaliacao.",
        pontos=50,
        periodicidade="por_os",
        icon="star_rounded",
    ),
    "pagar_em_dia": MissaoDef(
        slug_base="pagar_em_dia",
        titulo="Pague em dia",
        descricao="Cada fatura paga sem atraso vale 100 pts. So feliz, sem cobranca.",
        pontos=100,
        periodicidade="on_the_fly",
        icon="payments_rounded",
    ),
}


# ────────────────────── Conclusao (tabela) ──────────────────────


async def _ja_completou(
    session: AsyncSession, user_id: UUID, slug: str
) -> bool:
    stmt = (
        select(ClienteAppMissaoCompletada.id)
        .where(
            ClienteAppMissaoCompletada.cliente_app_user_id == user_id,
            ClienteAppMissaoCompletada.slug == slug,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def completar(
    session: AsyncSession,
    user_id: UUID,
    slug_base: str,
    *,
    chave_extra: str | None = None,
) -> bool:
    """Tenta registrar conclusao da missao. Idempotente (unique constraint).

    Retorna True se foi NOVA conclusao, False se ja tinha.
    Falha silenciosamente em qualquer outro erro — nao bloqueia o fluxo
    principal (share, NPS, etc).
    """
    if slug_base not in MISSOES:
        return False
    if slug_base == "share_indicacao":
        hoje = datetime.now(tz=UTC).date().isoformat()
        slug = f"{slug_base}:{hoje}"
    elif slug_base == "responder_nps":
        if not chave_extra:
            return False
        slug = f"{slug_base}:{chave_extra}"
    else:
        # Missao on_the_fly nao vai pra tabela.
        return False

    try:
        if await _ja_completou(session, user_id, slug):
            return False
        row = ClienteAppMissaoCompletada(
            cliente_app_user_id=user_id,
            slug=slug,
        )
        session.add(row)
        await session.flush()
        return True
    except IntegrityError:
        # Race condition — outro request gravou primeiro. OK.
        await session.rollback()
        return False
    except Exception as e:  # noqa: BLE001
        log.warning("missao.completar_falhou", slug=slug, error=str(e))
        return False


# ────────────────────── Calculo de pontos ──────────────────────


async def _count_completadas(
    session: AsyncSession, user_id: UUID, slug_base: str
) -> int:
    stmt = select(func.count()).select_from(ClienteAppMissaoCompletada).where(
        ClienteAppMissaoCompletada.cliente_app_user_id == user_id,
        ClienteAppMissaoCompletada.slug.like(f"{slug_base}:%"),
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def calcular_pontos_missoes(
    session: AsyncSession, user: ClienteAppUser
) -> tuple[int, dict[str, int]]:
    """Retorna (total_pts, contagem_por_missao).

    Contagem inclui 'pagar_em_dia' calculado on-the-fly via SGP.
    """
    contagem: dict[str, int] = {}

    # Discretas (tabela).
    for slug in ("share_indicacao", "responder_nps"):
        contagem[slug] = await _count_completadas(session, user.id, slug)

    # On-the-fly: pagar em dia = titulos SGP com status='pago' E dias_atraso==0
    pagas_em_dia = 0
    try:
        from ondeline_api.api.v1.cliente_app_me import _sgp_cliente

        sgp = await _sgp_cliente(session, user.cpf_encrypted)
        if sgp is not None:
            pagas_em_dia = sum(
                1
                for t in sgp.titulos
                if t.status == "pago" and (t.dias_atraso or 0) == 0
            )
    except Exception as e:  # noqa: BLE001
        log.warning("missao.pagar_em_dia_falhou", error=str(e))
    contagem["pagar_em_dia"] = pagas_em_dia

    total = sum(
        contagem.get(slug, 0) * defn.pontos for slug, defn in MISSOES.items()
    )
    return total, contagem


# ────────────────────── Status atual pra UI ──────────────────────


async def status_missoes(
    session: AsyncSession, user: ClienteAppUser
) -> list[dict[str, Any]]:
    """Lista de missoes com flag de progresso atual (pra UI).

    Para diaria: completada_hoje (bool).
    Para por_os: count total.
    Para on_the_fly: count total.
    """
    items: list[dict[str, Any]] = []
    hoje = datetime.now(tz=UTC).date().isoformat()

    for slug, defn in MISSOES.items():
        if defn.periodicidade == "diaria":
            slug_hoje = f"{slug}:{hoje}"
            done_hoje = await _ja_completou(session, user.id, slug_hoje)
            items.append(
                {
                    "slug": slug,
                    "titulo": defn.titulo,
                    "descricao": defn.descricao,
                    "pontos": defn.pontos,
                    "periodicidade": defn.periodicidade,
                    "icon": defn.icon,
                    "completada_hoje": done_hoje,
                    "total_concluida": await _count_completadas(
                        session, user.id, slug
                    ),
                }
            )
        elif defn.periodicidade == "por_os":
            count = await _count_completadas(session, user.id, slug)
            items.append(
                {
                    "slug": slug,
                    "titulo": defn.titulo,
                    "descricao": defn.descricao,
                    "pontos": defn.pontos,
                    "periodicidade": defn.periodicidade,
                    "icon": defn.icon,
                    "completada_hoje": False,
                    "total_concluida": count,
                }
            )
        else:  # on_the_fly
            total_pts, contagem = await calcular_pontos_missoes(session, user)
            count = contagem.get(slug, 0)
            items.append(
                {
                    "slug": slug,
                    "titulo": defn.titulo,
                    "descricao": defn.descricao,
                    "pontos": defn.pontos,
                    "periodicidade": defn.periodicidade,
                    "icon": defn.icon,
                    "completada_hoje": False,
                    "total_concluida": count,
                }
            )

    return items
