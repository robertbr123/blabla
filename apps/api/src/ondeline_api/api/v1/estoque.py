"""GET/POST /api/v1/estoque/* — itens, movimentos, saldo (F6)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.estoque import (
    ItemCreate,
    ItemOut,
    ItemUpdate,
    MovimentoCreate,
    MovimentoOut,
    SaldoLinha,
    SaldoOut,
)
from ondeline_api.api.v1.tecnico_me import current_tecnico
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.estoque import EstoqueItem
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.estoque import ItemRepo, MovimentoRepo
from ondeline_api.services.estoque import (
    EstoqueError,
    ItemNaoExiste,
    SaldoInsuficiente,
    SerialDuplicado,
    calcular_saldo_tecnico,
    registrar_movimento,
)

router = APIRouter(prefix="/api/v1/estoque", tags=["estoque"])

_admin = Depends(require_role(Role.ADMIN))
_admin_atendente = Depends(require_role(Role.ADMIN, Role.ATENDENTE))


# ── Catálogo ────────────────────────────────────────────────


@router.get("/itens", response_model=list[ItemOut], dependencies=[_admin_atendente])
async def list_itens(
    session: Annotated[AsyncSession, Depends(get_db)],
    ativos_only: bool = Query(False),
) -> list[ItemOut]:
    repo = ItemRepo(session)
    rows = await repo.list_all(ativos_only=ativos_only)
    return [ItemOut.model_validate(r) for r in rows]


@router.post(
    "/itens",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin],
)
async def create_item(
    body: ItemCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    item = EstoqueItem(
        sku=body.sku,
        nome=body.nome,
        categoria=body.categoria,
        serializado=body.serializado,
        ativo=body.ativo,
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="sku ja em uso") from e
    return ItemOut.model_validate(item)


@router.patch("/itens/{item_id}", response_model=ItemOut, dependencies=[_admin])
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ItemOut:
    repo = ItemRepo(session)
    item = await repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.flush()
    return ItemOut.model_validate(item)


# ── Saldo ────────────────────────────────────────────────


@router.get("/saldo", response_model=SaldoOut, dependencies=[_admin_atendente])
async def saldo_admin(
    session: Annotated[AsyncSession, Depends(get_db)],
    tecnico_id: UUID = Query(..., description="Técnico cujo saldo se quer ver"),
) -> SaldoOut:
    linhas = await calcular_saldo_tecnico(session, tecnico_id)
    return SaldoOut(
        tecnico_id=tecnico_id,
        linhas=[SaldoLinha.model_validate(l) for l in linhas],
    )


# Endpoint pra técnico ver o próprio saldo (sem precisar de admin).
_tec_router = APIRouter(prefix="/api/v1/tecnico/me/estoque", tags=["tecnico-me"])


@_tec_router.get(
    "/saldo",
    response_model=SaldoOut,
    dependencies=[Depends(require_role(Role.TECNICO))],
)
async def saldo_self(
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> SaldoOut:
    linhas = await calcular_saldo_tecnico(session, tec.id)
    return SaldoOut(
        tecnico_id=tec.id,
        linhas=[SaldoLinha.model_validate(l) for l in linhas],
    )


# ── Movimentos ────────────────────────────────────────────────


@router.post(
    "/movimentos",
    response_model=MovimentoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_atendente],
)
async def create_movimento(
    body: MovimentoCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovimentoOut:
    try:
        mov = await registrar_movimento(
            session,
            item_id=body.item_id,
            tipo=body.tipo,
            quantidade=body.quantidade,
            criado_por=user.id,
            tecnico_id=body.tecnico_id,
            serial=body.serial,
            ordem_servico_id=body.ordem_servico_id,
            observacao=body.observacao,
        )
    except SaldoInsuficiente as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ItemNaoExiste, SerialDuplicado) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EstoqueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MovimentoOut.model_validate(mov)


@router.get(
    "/movimentos",
    response_model=list[MovimentoOut],
    dependencies=[_admin_atendente],
)
async def list_movimentos(
    session: Annotated[AsyncSession, Depends(get_db)],
    tecnico_id: UUID | None = Query(None),
    item_id: UUID | None = Query(None),
    ordem_servico_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[MovimentoOut]:
    repo = MovimentoRepo(session)
    if tecnico_id is None and item_id is None and ordem_servico_id is None:
        rows = await repo.list_recentes_global(limit=limit)
    else:
        rows = await repo.list_by_tecnico(
            tecnico_id,
            item_id=item_id,
            ordem_servico_id=ordem_servico_id,
            limit=limit,
        )
    return [MovimentoOut.model_validate(r) for r in rows]


# Endpoint técnico-self: ver os próprios movimentos recentes.
@_tec_router.get(
    "/movimentos",
    response_model=list[MovimentoOut],
    dependencies=[Depends(require_role(Role.TECNICO))],
)
async def list_movimentos_self(
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    limit: int = Query(50, ge=1, le=200),
) -> list[MovimentoOut]:
    rows = await MovimentoRepo(session).list_by_tecnico(tec.id, limit=limit)
    return [MovimentoOut.model_validate(r) for r in rows]


# Exporta os dois routers; main.py registra ambos.
tecnico_estoque_router = _tec_router
