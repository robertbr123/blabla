"""Escopo de cidades do atendente.

Um atendente pode ser limitado a um conjunto de cidades (``users.cidades``).
A regra, aplicada a conversas e ordens de servico:

- admin e tecnico: sem restricao;
- atendente sem cidades marcadas: sem restricao;
- atendente com cidades: ve o registro se o cliente for de uma delas **ou**
  se ainda nao houver cidade conhecida (conversa sem cliente identificado,
  cliente sem cidade) — contato novo nunca fica sem dono.

A comparacao ignora caixa, acento e espacos nas pontas ("Eirunepé" casa com
"EIRUNEPE"), porque a cidade vem do SGP em texto livre.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.deps import get_current_user
from ondeline_api.db.models.business import Cliente, Conversa, OrdemServico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db

# Mesmo mapa nos dois lados (Python e SQL) — se mudar um, muda o outro.
_ACENTOS_DE = "áàâãäéèêëíìîïóòôõöúùûüçñ"
_ACENTOS_PARA = "aaaaaeeeeiiiiooooouuuucn"


def normalize_cidade(value: str) -> str:
    """minusculas, sem acento, sem espaco nas pontas."""
    s = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def cidade_norm_sql(col: Any) -> ColumnElement[str]:
    """Equivalente SQL de ``normalize_cidade`` (sem depender de extensao unaccent)."""
    return func.translate(func.lower(func.trim(col)), _ACENTOS_DE, _ACENTOS_PARA)


def clean_cidades(values: list[str] | None) -> list[str]:
    """Tira vazios e duplicatas (por forma normalizada), preservando a grafia."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        v = raw.strip()
        key = normalize_cidade(v)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def user_scope(user: User) -> list[str] | None:
    """Cidades (normalizadas) a que o usuario esta limitado; None = ve tudo."""
    if user.role != Role.ATENDENTE:
        return None
    cidades = [normalize_cidade(c) for c in (user.cidades or [])]
    cidades = [c for c in cidades if c]
    return cidades or None


def cliente_in_scope(cliente_id_col: Any, cidades: list[str]) -> ColumnElement[bool]:
    """Filtro pra uma coluna ``cliente_id``: sem cliente, sem cidade, ou cidade no escopo."""
    permitidos = select(Cliente.id).where(
        or_(
            Cliente.cidade.is_(None),
            func.trim(Cliente.cidade) == "",
            cidade_norm_sql(Cliente.cidade).in_(cidades),
        )
    )
    return or_(cliente_id_col.is_(None), cliente_id_col.in_(permitidos))


async def get_scope(user: User = Depends(get_current_user)) -> list[str] | None:  # noqa: B008
    """Dependency pra listagens: devolve o escopo do usuario logado."""
    return user_scope(user)


def require_scoped_role(
    *allowed: Role, param: str, model: type[Conversa] | type[OrdemServico]
) -> Callable[..., Awaitable[User]]:
    """``require_role`` + checagem de escopo no registro da rota.

    Se a rota tem o path param ``param`` (ex.: ``conversa_id``), carrega o
    ``cliente_id`` do registro e devolve 404 quando ele esta fora das cidades
    do atendente — 404 e nao 403 pra nao confirmar que o registro existe.
    Rotas sem o param (listagem, criacao) so passam pela checagem de role.
    """
    allowed_set = set(allowed)

    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),  # noqa: B008
        session: AsyncSession = Depends(get_db),  # noqa: B008
    ) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role"
            )
        cidades = user_scope(user)
        raw = request.path_params.get(param)
        if cidades is None or raw is None:
            return user
        try:
            record_id = UUID(str(raw))
        except ValueError:
            return user  # a propria rota responde 422
        stmt = select(model.id).where(
            model.id == record_id, cliente_in_scope(model.cliente_id, cidades)
        )
        if (await session.execute(stmt)).scalar_one_or_none() is None:
            # Fora do escopo OU inexistente: a mesma resposta nos dois casos.
            raise HTTPException(status_code=404, detail="not found")
        return user

    return _dep
