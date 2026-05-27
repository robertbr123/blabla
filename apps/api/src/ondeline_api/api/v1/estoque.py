"""GET/POST /api/v1/estoque/* — itens, movimentos, saldo (F6)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.estoque import (
    CategoriaCreate,
    CategoriaOut,
    CategoriaUpdate,
    DepositoBaixaIn,
    DepositoEntradaIn,
    DepositoSaldoOut,
    DevolverIn,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    MovimentoCreate,
    MovimentoOut,
    SaldoLinha,
    SaldoOut,
    SeriaisAtivosOut,
    SerialAtivo,
    TecnicoSaldoOut,
    TecnicoSaldoResumo,
    TransferirIn,
)
from ondeline_api.api.v1.tecnico_me import current_tecnico
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.estoque import EstoqueCategoria, EstoqueItem
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.estoque import ItemRepo, MovimentoRepo
from ondeline_api.services.estoque import (
    EstoqueError,
    ItemNaoExiste,
    SaldoInsuficiente,
    SerialDuplicado,
    calcular_saldo_tecnico,
    devolver_tecnico_para_deposito,
    registrar_movimento,
    transferir_deposito_para_tecnico,
)

router = APIRouter(prefix="/api/v1/estoque", tags=["estoque"])

_admin = Depends(require_role(Role.ADMIN))
_admin_atendente = Depends(require_role(Role.ADMIN, Role.ATENDENTE))


# ── Catálogo ────────────────────────────────────────────────


@router.get("/itens", response_model=list[ItemOut], dependencies=[_admin_atendente])
async def list_itens(
    session: Annotated[AsyncSession, Depends(get_db)],
    ativos_only: Annotated[bool, Query()] = False,
) -> list[ItemOut]:
    repo = ItemRepo(session)
    rows = await repo.list_all(ativos_only=ativos_only)
    return [ItemOut.model_validate(r) for r in rows]


async def _validar_categoria(session: AsyncSession, slug: str) -> None:
    from sqlalchemy import select

    row = (
        await session.execute(
            select(EstoqueCategoria).where(
                EstoqueCategoria.slug == slug, EstoqueCategoria.ativo.is_(True)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=400, detail=f"categoria '{slug}' nao cadastrada ou inativa"
        )


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
    await _validar_categoria(session, body.categoria)
    item = EstoqueItem(
        sku=body.sku,
        nome=body.nome,
        categoria=body.categoria,
        unidade=body.unidade,
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
    if body.categoria is not None:
        await _validar_categoria(session, body.categoria)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.flush()
    return ItemOut.model_validate(item)


# ── Categorias ────────────────────────────────────────────────


@router.get(
    "/categorias",
    response_model=list[CategoriaOut],
    dependencies=[_admin_atendente],
)
async def list_categorias(
    session: Annotated[AsyncSession, Depends(get_db)],
    ativos_only: Annotated[bool, Query()] = False,
) -> list[CategoriaOut]:
    from sqlalchemy import select

    stmt = select(EstoqueCategoria)
    if ativos_only:
        stmt = stmt.where(EstoqueCategoria.ativo.is_(True))
    stmt = stmt.order_by(EstoqueCategoria.nome)
    rows = list((await session.execute(stmt)).scalars().all())
    return [CategoriaOut.model_validate(r) for r in rows]


@router.post(
    "/categorias",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin],
)
async def create_categoria(
    body: CategoriaCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CategoriaOut:
    cat = EstoqueCategoria(slug=body.slug, nome=body.nome, ativo=body.ativo)
    session.add(cat)
    try:
        await session.flush()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="slug ja em uso") from e
    return CategoriaOut.model_validate(cat)


@router.patch(
    "/categorias/{cat_id}",
    response_model=CategoriaOut,
    dependencies=[_admin],
)
async def update_categoria(
    cat_id: UUID,
    body: CategoriaUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CategoriaOut:
    from sqlalchemy import select

    cat = (
        await session.execute(
            select(EstoqueCategoria).where(EstoqueCategoria.id == cat_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="categoria not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    await session.flush()
    return CategoriaOut.model_validate(cat)


@router.delete(
    "/categorias/{cat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin],
)
async def delete_categoria(
    cat_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    from sqlalchemy import func, select

    cat = (
        await session.execute(
            select(EstoqueCategoria).where(EstoqueCategoria.id == cat_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail="categoria not found")

    n = (
        await session.execute(
            select(func.count(EstoqueItem.id)).where(EstoqueItem.categoria == cat.slug)
        )
    ).scalar_one()
    if n and n > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"categoria tem {n} item(ns) — nao da pra apagar. "
                "Desative via PATCH ativo=false."
            ),
        )
    await session.delete(cat)
    await session.flush()


@router.delete(
    "/itens/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin],
)
async def delete_item(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Exclui um item do catalogo.

    - Se nao tem nenhum movimento, faz hard delete.
    - Se tem movimentos (mesmo zerados), retorna 409 sugerindo desativar
      via PATCH (preserva historico).
    """
    from sqlalchemy import func, select

    from ondeline_api.db.models.estoque import EstoqueMovimento

    repo = ItemRepo(session)
    item = await repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")

    n_movs = (
        await session.execute(
            select(func.count(EstoqueMovimento.id)).where(
                EstoqueMovimento.item_id == item_id
            )
        )
    ).scalar_one()
    if n_movs and n_movs > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"item tem {n_movs} movimento(s) registrado(s) — nao da pra "
                "apagar (perderia historico). Desative em vez disso "
                "(PATCH /itens/{id} com ativo=false)."
            ),
        )

    await session.delete(item)
    await session.flush()


# ── Saldo ────────────────────────────────────────────────


@router.get("/saldo", response_model=SaldoOut, dependencies=[_admin_atendente])
async def saldo_admin(
    session: Annotated[AsyncSession, Depends(get_db)],
    tecnico_id: Annotated[
        UUID, Query(description="Técnico cujo saldo se quer ver")
    ],
) -> SaldoOut:
    linhas = await calcular_saldo_tecnico(session, tecnico_id)
    return SaldoOut(
        tecnico_id=tecnico_id,
        linhas=[SaldoLinha.model_validate(ln) for ln in linhas],
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
        linhas=[SaldoLinha.model_validate(ln) for ln in linhas],
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
    tecnico_id: Annotated[UUID | None, Query()] = None,
    item_id: Annotated[UUID | None, Query()] = None,
    ordem_servico_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
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
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[MovimentoOut]:
    rows = await MovimentoRepo(session).list_by_tecnico(tec.id, limit=limit)
    return [MovimentoOut.model_validate(r) for r in rows]


# F6+ — Tecnico registra movimento do PROPRIO estoque.
# Tipos permitidos: `saida` (instalou no cliente) e `recolhido` (trouxe do
# cliente). Outros tipos (entrada/devolucao/perda/ajustes) sao admin-only —
# tecnico nao pode entregar pra si proprio nem mexer em ajustes contabeis.
class TecMovimentoIn(BaseModel):
    item_id: UUID
    tipo: str = Field(pattern="^(saida|recolhido)$")
    quantidade: int = Field(gt=0)
    serial: str | None = Field(default=None, max_length=120)
    ordem_servico_id: UUID | None = None
    observacao: str | None = None


@_tec_router.post(
    "/movimentos",
    response_model=MovimentoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.TECNICO))],
)
async def create_movimento_self(
    body: TecMovimentoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovimentoOut:
    try:
        mov = await registrar_movimento(
            session,
            item_id=body.item_id,
            tipo=body.tipo,
            quantidade=body.quantidade,
            criado_por=user.id,
            tecnico_id=tec.id,  # SEMPRE o proprio tecnico
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


# ── Depósito (estoque central) ─────────────────────────────────
#
# Convencao: `tecnico_id IS NULL` em estoque_movimento = movimento do
# deposito central. Endpoints aqui sao operacoes do admin/atendente:
#   - GET  /api/v1/estoque/deposito/saldo     -> o que tem no deposito
#   - POST /api/v1/estoque/deposito/entrada   -> recebimento (fornecedor)
#   - POST /api/v1/estoque/deposito/baixa     -> perda/ajuste sem destino
#   - POST /api/v1/estoque/deposito/transferir-> deposito -> tecnico (atomic)
#   - GET  /api/v1/estoque/tecnicos/saldos    -> visao agregada por tecnico


@router.get(
    "/deposito/saldo",
    response_model=DepositoSaldoOut,
    dependencies=[_admin_atendente],
)
async def saldo_deposito(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DepositoSaldoOut:
    rows = await MovimentoRepo(session).saldo_full_deposito()
    linhas = [
        SaldoLinha(
            item_id=str(item.id),
            sku=item.sku,
            nome=item.nome,
            categoria=item.categoria,
            unidade=item.unidade,
            serializado=item.serializado,
            saldo=saldo,
        )
        for item, saldo in rows
    ]
    return DepositoSaldoOut(linhas=linhas)


@router.post(
    "/deposito/entrada",
    response_model=MovimentoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_atendente],
)
async def entrada_deposito(
    body: DepositoEntradaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovimentoOut:
    """Lancamento de entrada no deposito (compra, recebimento de fornecedor).
    Movimento (tecnico_id=NULL, tipo=entrada).
    """
    try:
        mov = await registrar_movimento(
            session,
            item_id=body.item_id,
            tipo="entrada",
            quantidade=body.quantidade,
            criado_por=user.id,
            tecnico_id=None,
            serial=body.serial,
            observacao=body.observacao,
        )
    except (ItemNaoExiste, SerialDuplicado) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EstoqueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MovimentoOut.model_validate(mov)


@router.post(
    "/deposito/baixa",
    response_model=MovimentoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin],
)
async def baixa_deposito(
    body: DepositoBaixaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovimentoOut:
    """Baixa direta no deposito (perda, ajuste negativo). Nao envia pra tecnico."""
    try:
        mov = await registrar_movimento(
            session,
            item_id=body.item_id,
            tipo=body.tipo,
            quantidade=body.quantidade,
            criado_por=user.id,
            tecnico_id=None,
            serial=body.serial,
            observacao=body.observacao,
        )
    except SaldoInsuficiente as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ItemNaoExiste, SerialDuplicado) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EstoqueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return MovimentoOut.model_validate(mov)


@router.post(
    "/deposito/transferir",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_atendente],
)
async def transferir_deposito(
    body: TransferirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Transferencia atomica deposito -> tecnico (saida + entrada)."""
    try:
        saida, entrada = await transferir_deposito_para_tecnico(
            session,
            item_id=body.item_id,
            tecnico_id=body.tecnico_id,
            quantidade=body.quantidade,
            criado_por=user.id,
            serial=body.serial,
            observacao=body.observacao,
        )
    except SaldoInsuficiente as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ItemNaoExiste, SerialDuplicado) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EstoqueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"saida_id": str(saida.id), "entrada_id": str(entrada.id)}


@router.post(
    "/deposito/devolver",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_admin_atendente],
)
async def devolver_para_deposito(
    body: DevolverIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Devolucao atomica tecnico -> deposito (devolucao + entrada)."""
    try:
        saida, entrada = await devolver_tecnico_para_deposito(
            session,
            item_id=body.item_id,
            tecnico_id=body.tecnico_id,
            quantidade=body.quantidade,
            criado_por=user.id,
            serial=body.serial,
            observacao=body.observacao,
        )
    except SaldoInsuficiente as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ItemNaoExiste, SerialDuplicado) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except EstoqueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"saida_id": str(saida.id), "entrada_id": str(entrada.id)}


@router.get(
    "/tecnicos/saldos",
    response_model=TecnicoSaldoOut,
    dependencies=[_admin_atendente],
)
async def saldos_tecnicos(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TecnicoSaldoOut:
    """Visao admin: saldo por tecnico x item (apenas linhas com saldo > 0).

    Permite ao admin ver o que cada tecnico tem em maos.
    """
    from sqlalchemy import case, func, select

    from ondeline_api.db.models.business import Tecnico as TecnicoModel
    from ondeline_api.db.models.estoque import (
        TIPOS_POSITIVOS as _POS,
    )
    from ondeline_api.db.models.estoque import EstoqueMovimento

    sign = case(
        (EstoqueMovimento.tipo.in_(list(_POS)), EstoqueMovimento.quantidade),
        else_=-EstoqueMovimento.quantidade,
    )
    stmt = (
        select(
            TecnicoModel.id.label("tec_id"),
            TecnicoModel.nome.label("tec_nome"),
            EstoqueItem.id.label("item_id"),
            EstoqueItem.sku,
            EstoqueItem.nome.label("item_nome"),
            EstoqueItem.categoria,
            EstoqueItem.unidade,
            func.coalesce(func.sum(sign), 0).label("saldo"),
        )
        .select_from(EstoqueMovimento)
        .join(TecnicoModel, TecnicoModel.id == EstoqueMovimento.tecnico_id)
        .join(EstoqueItem, EstoqueItem.id == EstoqueMovimento.item_id)
        .where(EstoqueItem.ativo.is_(True))
        .group_by(
            TecnicoModel.id,
            TecnicoModel.nome,
            EstoqueItem.id,
            EstoqueItem.sku,
            EstoqueItem.nome,
            EstoqueItem.categoria,
            EstoqueItem.unidade,
        )
        .having(func.coalesce(func.sum(sign), 0) > 0)
        .order_by(TecnicoModel.nome, EstoqueItem.nome)
    )
    rows = (await session.execute(stmt)).all()
    linhas = [
        TecnicoSaldoResumo(
            tecnico_id=r.tec_id,
            tecnico_nome=r.tec_nome,
            item_id=r.item_id,
            sku=r.sku,
            nome=r.item_nome,
            categoria=r.categoria,
            unidade=r.unidade,
            saldo=int(r.saldo),
        )
        for r in rows
    ]
    return TecnicoSaldoOut(linhas=linhas)


@router.get(
    "/seriais",
    response_model=SeriaisAtivosOut,
    dependencies=[_admin_atendente],
)
async def list_seriais_ativos(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SeriaisAtivosOut:
    """Lista seriais que estao atualmente em estoque (saldo do serial > 0).

    Para cada (item_id, serial), pega o ultimo movimento; se o tipo for
    positivo (entrada/recolhido/ajuste+), o serial esta naquela localizacao
    (tecnico_id ou deposito quando NULL). Tipos negativos ja sairam do estoque.
    """
    from sqlalchemy import select

    from ondeline_api.db.models.estoque import (
        TIPOS_POSITIVOS as _POS,
    )
    from ondeline_api.db.models.estoque import EstoqueMovimento

    # DISTINCT ON: ultimo movimento por (item_id, serial)
    last_mov = (
        select(
            EstoqueMovimento.item_id,
            EstoqueMovimento.serial,
            EstoqueMovimento.tecnico_id,
            EstoqueMovimento.tipo,
            EstoqueMovimento.criado_em,
        )
        .where(EstoqueMovimento.serial.is_not(None))
        .order_by(
            EstoqueMovimento.item_id,
            EstoqueMovimento.serial,
            EstoqueMovimento.criado_em.desc(),
        )
        .distinct(EstoqueMovimento.item_id, EstoqueMovimento.serial)
    ).subquery()

    stmt = select(
        last_mov.c.item_id,
        last_mov.c.serial,
        last_mov.c.tecnico_id,
        last_mov.c.criado_em,
    ).where(last_mov.c.tipo.in_(list(_POS)))

    rows = (await session.execute(stmt)).all()
    linhas = [
        SerialAtivo(
            item_id=r.item_id,
            serial=r.serial,
            tecnico_id=r.tecnico_id,
            desde=r.criado_em,
        )
        for r in rows
    ]
    return SeriaisAtivosOut(linhas=linhas)


# Exporta os dois routers; main.py registra ambos.
tecnico_estoque_router = _tec_router
