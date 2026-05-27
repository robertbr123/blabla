"""GET /api/v1/cliente-app/manutencoes — manutencoes ATIVAS pra cidade do user.

Diferente do /api/v1/manutencoes (admin), este endpoint:
- exige token cliente
- filtra apenas manutencoes em andamento agora (inicio_at <= now <= fim_at)
- filtra pela cidade do contrato selecionado (ou todos contratos do CPF)
- retorna estrutura enxuta pra renderizar a marquee bar
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db
from ondeline_api.repositories.manutencao import ManutencaoRepo

router = APIRouter(
    prefix="/api/v1/cliente-app/manutencoes",
    tags=["cliente-app:manutencoes"],
)


class ManutencaoBreakingOut(BaseModel):
    id: str
    titulo: str
    descricao: str | None = None
    inicio_at: str
    fim_at: str


class ManutencoesBreakingOut(BaseModel):
    items: list[ManutencaoBreakingOut]


def _cidades_do_user(sgp_contratos: list) -> list[str]:
    """Coleta todas as cidades distintas dos contratos do user (case-insensitive)."""
    seen: dict[str, str] = {}
    for c in sgp_contratos:
        cidade = (c.cidade or "").strip()
        if cidade:
            seen.setdefault(cidade.lower(), cidade)
    return list(seen.values())


@router.get("", response_model=ManutencoesBreakingOut)
async def listar(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ManutencoesBreakingOut:
    from ondeline_api.api.v1.cliente_app_me import _sgp_cliente

    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    cidades = _cidades_do_user(list(sgp.contratos)) if sgp else []

    repo = ManutencaoRepo(session)
    if not cidades:
        # Sem cidade conhecida — mostra so as globais (cidades=None).
        all_active = await repo.list_active_in_cidade("")
        items = [m for m in all_active if not m.cidades]
    else:
        # Une o resultado de cada cidade do user, deduplicado por id.
        seen_ids: set = set()
        items = []
        for cidade in cidades:
            for m in await repo.list_active_in_cidade(cidade):
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    items.append(m)
        # Ordena por inicio_at desc (mais recentes primeiro).
        items.sort(key=lambda m: m.inicio_at, reverse=True)

    out = [
        ManutencaoBreakingOut(
            id=str(m.id),
            titulo=m.titulo,
            descricao=m.descricao,
            inicio_at=m.inicio_at.isoformat(),
            fim_at=m.fim_at.isoformat(),
        )
        for m in items
    ]
    return ManutencoesBreakingOut(items=out)
