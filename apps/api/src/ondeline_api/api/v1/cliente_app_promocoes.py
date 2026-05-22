"""Routers de promoções.

- `/api/v1/cliente-app/promocoes` — cliente lista promoções ativas pro proprio segmento.
- `/api/v1/admin/promocoes` — admin CRUD + reorder + upload imagem + metricas.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.promocao import (
    PromocaoAdminOut,
    PromocaoCreateIn,
    PromocaoEventoIn,
    PromocaoEventoOut,
    PromocaoOut,
    PromocaoReorderIn,
    PromocaoUpdateIn,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.identity import Role, User
from ondeline_api.db.models.promocoes import Promocao, PromocaoEvento
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

# Diretorio dos uploads de imagem. Servido em /static/promocoes/.
STATIC_DIR = Path("data/static/promocoes")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# ════════════════════════ Cliente router ════════════════════════

router = APIRouter(prefix="/api/v1/cliente-app/promocoes", tags=["cliente-app:promocoes"])


def _promo_out(p: Promocao) -> PromocaoOut:
    return PromocaoOut(
        id=p.id,
        titulo=p.titulo,
        subtitulo=p.subtitulo,
        imagem_url=p.imagem_url,
        cta_label=p.cta_label,
        cta_action=p.cta_action,
        tipo=p.tipo,
        ativa=p.ativa,
        ordem=p.ordem,
        valido_de=p.valido_de,
        valido_ate=p.valido_ate,
        segmento=p.segmento,
        gradient_from=p.gradient_from,
        gradient_to=p.gradient_to,
        icon=p.icon,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _segmento_aplicavel(segmento: str, _user: ClienteAppUser) -> bool:
    """Filtro de segmentacao. Por ora so 'todos' aplica universalmente.

    Os demais segmentos (inadimplentes/adimplentes/plano:X) exigem consulta
    SGP em runtime — TODO: implementar quando tiver helper consolidado.
    Enquanto isso, qualquer segmento != 'todos' fica oculto pra evitar
    mostrar promo errada pro cliente errado.
    """
    return segmento == "todos"


@router.get("", response_model=list[PromocaoOut])
async def listar_para_cliente(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoOut]:
    now = datetime.now(tz=UTC)
    stmt = (
        select(Promocao)
        .where(Promocao.ativa.is_(True))
        .order_by(asc(Promocao.ordem), asc(Promocao.created_at))
    )
    rows = list((await session.execute(stmt)).scalars())
    out: list[PromocaoOut] = []
    for p in rows:
        if p.valido_de is not None and p.valido_de > now:
            continue
        if p.valido_ate is not None and p.valido_ate < now:
            continue
        if not _segmento_aplicavel(p.segmento, user):
            continue
        out.append(_promo_out(p))
    return out


@router.post("/{promo_id}/evento", response_model=PromocaoEventoOut)
async def registrar_evento(
    promo_id: UUID,
    body: PromocaoEventoIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoEventoOut:
    promo = await session.get(Promocao, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    ev = PromocaoEvento(
        promocao_id=promo_id,
        cliente_app_user_id=user.id,
        tipo=body.tipo,
    )
    session.add(ev)
    await session.commit()
    return PromocaoEventoOut(ok=True)


# ════════════════════════ Admin router ════════════════════════

admin_router = APIRouter(
    prefix="/api/v1/admin/promocoes",
    tags=["admin:promocoes"],
)


async def _stats(session: AsyncSession, promo_id: UUID) -> tuple[int, int]:
    rows = (
        await session.execute(
            select(PromocaoEvento.tipo, func.count())
            .where(PromocaoEvento.promocao_id == promo_id)
            .group_by(PromocaoEvento.tipo)
        )
    ).all()
    by = {t: int(c) for t, c in rows}
    return by.get("view", 0), by.get("click", 0)


def _admin_out(p: Promocao, views: int, clicks: int) -> PromocaoAdminOut:
    base = _promo_out(p)
    ctr = (clicks / views * 100.0) if views > 0 else 0.0
    return PromocaoAdminOut(
        **base.model_dump(),
        views=views,
        clicks=clicks,
        ctr=round(ctr, 2),
    )


@admin_router.get(
    "",
    response_model=list[PromocaoAdminOut],
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_listar(
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoAdminOut]:
    stmt = select(Promocao).order_by(asc(Promocao.ordem), asc(Promocao.created_at))
    rows = list((await session.execute(stmt)).scalars())
    out: list[PromocaoAdminOut] = []
    for p in rows:
        v, c = await _stats(session, p.id)
        out.append(_admin_out(p, v, c))
    return out


@admin_router.post(
    "",
    response_model=PromocaoAdminOut,
    status_code=201,
)
async def admin_criar(
    body: PromocaoCreateIn,
    current_user: User = Depends(require_role(Role.ADMIN)),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    promo = Promocao(
        **body.model_dump(),
        created_by=current_user.id,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return _admin_out(promo, 0, 0)


@admin_router.get(
    "/{promo_id}",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def admin_detalhe(
    promo_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    v, c = await _stats(session, p.id)
    return _admin_out(p, v, c)


@admin_router.patch(
    "/{promo_id}",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_atualizar(
    promo_id: UUID,
    body: PromocaoUpdateIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    await session.commit()
    await session.refresh(p)
    views, clicks = await _stats(session, p.id)
    return _admin_out(p, views, clicks)


@admin_router.delete(
    "/{promo_id}",
    status_code=204,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_remover(
    promo_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")
    # Remove imagem fisica se houver e for nosso static
    if p.imagem_url and p.imagem_url.startswith("/static/promocoes/"):
        fname = Path(p.imagem_url).name
        f = STATIC_DIR / fname
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass
    await session.delete(p)
    await session.commit()


@admin_router.post(
    "/reorder",
    response_model=list[PromocaoAdminOut],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_reorder(
    body: PromocaoReorderIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[PromocaoAdminOut]:
    for idx, pid in enumerate(body.ids):
        p = await session.get(Promocao, pid)
        if p is None:
            continue
        p.ordem = idx
    await session.commit()
    return await admin_listar(session=session)


@admin_router.post(
    "/{promo_id}/imagem",
    response_model=PromocaoAdminOut,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_upload_imagem(
    promo_id: UUID,
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromocaoAdminOut:
    p = await session.get(Promocao, promo_id)
    if p is None:
        raise HTTPException(status_code=404, detail="promocao nao encontrada")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"tipo invalido (use: {sorted(ALLOWED_EXT)})",
        )

    fname = f"{uuid.uuid4().hex}{suffix}"
    fpath = STATIC_DIR / fname
    bytes_written = 0
    with fpath.open("wb") as out:
        while chunk := await file.read(1024 * 64):
            bytes_written += len(chunk)
            if bytes_written > MAX_BYTES:
                out.close()
                fpath.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="imagem maior que 2MB")
            out.write(chunk)

    # Remove imagem antiga se for nosso static
    if p.imagem_url and p.imagem_url.startswith("/static/promocoes/"):
        old = STATIC_DIR / Path(p.imagem_url).name
        if old.exists() and old.name != fname:
            try:
                old.unlink()
            except OSError:
                pass

    p.imagem_url = f"/static/promocoes/{fname}"
    await session.commit()
    await session.refresh(p)
    v, c = await _stats(session, p.id)
    return _admin_out(p, v, c)
