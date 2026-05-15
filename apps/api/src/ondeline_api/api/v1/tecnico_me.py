"""GET/POST /api/v1/tecnico/me/* — endpoints do tecnico em campo."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.os import OsListItem, OsOut
from ondeline_api.api.schemas.tecnico_me import ConcluirIn, GpsUpdate, IniciarIn
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import Tecnico
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo

router = APIRouter(prefix="/api/v1/tecnico/me", tags=["tecnico-me"])
_role_dep = Depends(require_role(Role.TECNICO))

FOTOS_DIR = Path("/tmp/ondeline_os_fotos")


async def current_tecnico(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Tecnico:
    repo = TecnicoRepo(session)
    tec = await repo.get_by_user_id(user.id)
    if tec is None:
        raise HTTPException(status_code=403, detail="user is not a tecnico")
    return tec


@router.get("/os", response_model=list[OsListItem], dependencies=[_role_dep])
async def my_os(
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[OsListItem]:
    from sqlalchemy import select
    from ondeline_api.db.models.business import Cliente
    from ondeline_api.db.crypto import decrypt_pii

    repo = OrdemServicoRepo(session)
    rows = await repo.list_for_tecnico(tec.id, status_filter=status_filter)

    cliente_ids = [r.cliente_id for r in rows if r.cliente_id is not None]
    nomes: dict = {}
    if cliente_ids:
        cli_rows = (await session.execute(
            select(Cliente).where(Cliente.id.in_(cliente_ids))
        )).scalars().all()
        nomes = {c.id: decrypt_pii(c.nome_encrypted) for c in cli_rows}

    result = []
    for o in rows:
        item = OsListItem.model_validate(o)
        item.nome_cliente = nomes.get(o.cliente_id) if o.cliente_id else None
        result.append(item)
    return result


@router.get("/os/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def my_os_detail(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    return OsOut.model_validate(os_)


@router.post("/gps", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_role_dep])
async def update_gps(
    body: GpsUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> None:
    repo = TecnicoRepo(session)
    await repo.update_gps(tec, lat=body.lat, lng=body.lng)


@router.post(
    "/os/{os_id}/iniciar",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def iniciar_os(
    os_id: UUID,
    body: IniciarIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    await repo.set_iniciada_with_gps(os_, lat=body.lat, lng=body.lng)
    return OsOut.model_validate(os_)


@router.post(
    "/os/{os_id}/concluir",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def concluir_os(
    os_id: UUID,
    body: ConcluirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    await repo.set_concluida_with_gps(
        os_,
        csat=body.csat,
        comentario=body.comentario,
        relatorio=body.relatorio,
        houve_visita=body.houve_visita,
        materiais=body.materiais,
        lat=body.lat,
        lng=body.lng,
    )
    return OsOut.model_validate(os_)


@router.post(
    "/os/{os_id}/foto",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def upload_foto_my_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    file: Annotated[UploadFile, File()],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id_and_tecnico(os_id, tec.id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not assigned to you")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")
    target_dir = FOTOS_DIR / str(os_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid4().hex}{Path(file.filename or 'foto.jpg').suffix or '.jpg'}"
    fpath = target_dir / fname
    contents = await file.read()
    fpath.write_bytes(contents)
    fpath.chmod(0o600)
    await repo.add_foto(
        os_,
        {
            "url": str(fpath),
            "ts": datetime.now(tz=UTC).isoformat(),
            "size": len(contents),
            "mime": file.content_type,
        },
    )
    return OsOut.model_validate(os_)
