"""GET/POST /api/v1/tecnico/me/* — endpoints do tecnico em campo."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.schemas.os import OsListItem, OsOut
from ondeline_api.api.schemas.tecnico_me import (
    ConcluirIn,
    FcmTokenIn,
    FcmTokenRevokeIn,
    GpsUpdate,
    IniciarIn,
    MudarSenhaIn,
    PerfilEstatisticas,
    PerfilOut,
)
from ondeline_api.api.v1.ordens_servico import _fetch_nome_cliente
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
    from ondeline_api.api.v1.ordens_servico import _batch_nomes_clientes

    repo = OrdemServicoRepo(session)
    rows = await repo.list_for_tecnico(tec.id, status_filter=status_filter)
    nomes = await _batch_nomes_clientes(session, {o.cliente_id for o in rows if o.cliente_id})

    result = []
    for o in rows:
        item = OsListItem.model_validate(o)
        item.nome_cliente = nomes.get(o.cliente_id) if o.cliente_id is not None else None
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
    out = OsOut.model_validate(os_)
    out.nome_cliente = (await _fetch_nome_cliente(session, os_.cliente_id)) or os_.nome_sgp
    return out


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
    out = OsOut.model_validate(os_)
    out.nome_cliente = (await _fetch_nome_cliente(session, os_.cliente_id)) or os_.nome_sgp
    return out


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
    out = OsOut.model_validate(os_)
    out.nome_cliente = (await _fetch_nome_cliente(session, os_.cliente_id)) or os_.nome_sgp
    return out


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
    out = OsOut.model_validate(os_)
    out.nome_cliente = (await _fetch_nome_cliente(session, os_.cliente_id)) or os_.nome_sgp
    return out


# ── FCM device tokens ──────────────────────────────────────────────


@router.post(
    "/fcm-token",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def register_fcm_token(
    body: FcmTokenIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Registra (ou atualiza) o FCM/APNs token do dispositivo do tecnico.

    Idempotente: se o token ja existe globalmente, transfere pro user atual e
    atualiza last_seen_at. Limpa revoked_at se estava revogado.
    """
    from sqlalchemy import select

    from ondeline_api.db.models.identity import DeviceToken

    now = datetime.now(tz=UTC)
    existing = (
        await session.execute(
            select(DeviceToken).where(DeviceToken.token == body.token)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.user_id = user.id
        existing.platform = body.platform
        existing.last_seen_at = now
        existing.revoked_at = None
    else:
        session.add(
            DeviceToken(
                user_id=user.id,
                token=body.token,
                platform=body.platform,
                last_seen_at=now,
            )
        )
    await session.flush()


@router.post(
    "/fcm-token/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def revoke_fcm_token(
    body: FcmTokenRevokeIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Marca o token como revogado (logout). Nao deleta — preserva audit."""
    from sqlalchemy import select

    from ondeline_api.db.models.identity import DeviceToken

    existing = (
        await session.execute(
            select(DeviceToken).where(
                DeviceToken.token == body.token, DeviceToken.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.revoked_at = datetime.now(tz=UTC)
        await session.flush()


# ── Perfil + foto + senha ─────────────────────────────────────────


def _processar_foto(raw: bytes) -> str:
    """Redimensiona pra 256x256, JPEG quality 85, retorna base64 puro
    (sem data URL prefix). Levanta ValueError se nao for imagem valida.
    """
    import base64
    import io
    from typing import Any, cast

    from PIL import Image

    img: Any = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((256, 256), cast(Any, Image.Resampling.LANCZOS))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


@router.get("/perfil", response_model=PerfilOut, dependencies=[_role_dep])
async def get_perfil(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
) -> PerfilOut:
    """Retorna perfil completo do tecnico: dados + estatisticas do mes."""
    from datetime import timedelta

    from sqlalchemy import func, select

    from ondeline_api.db.models.business import OrdemServico, OsStatus

    now = datetime.now(tz=UTC)
    inicio_mes = datetime(now.year, now.month, 1, tzinfo=UTC)

    pendentes = (
        await session.execute(
            select(func.count(OrdemServico.id)).where(
                OrdemServico.tecnico_id == tec.id,
                OrdemServico.status == OsStatus.PENDENTE,
            )
        )
    ).scalar_one()

    em_andamento = (
        await session.execute(
            select(func.count(OrdemServico.id)).where(
                OrdemServico.tecnico_id == tec.id,
                OrdemServico.status == OsStatus.EM_ANDAMENTO,
            )
        )
    ).scalar_one()

    concluidas_mes = (
        await session.execute(
            select(func.count(OrdemServico.id)).where(
                OrdemServico.tecnico_id == tec.id,
                OrdemServico.status == OsStatus.CONCLUIDA,
                OrdemServico.concluida_em >= inicio_mes,
            )
        )
    ).scalar_one()

    csat_avg = (
        await session.execute(
            select(func.avg(OrdemServico.csat)).where(
                OrdemServico.tecnico_id == tec.id,
                OrdemServico.csat.isnot(None),
                OrdemServico.concluida_em >= inicio_mes,
            )
        )
    ).scalar_one()

    _ = timedelta  # silence unused

    return PerfilOut(
        user_id=str(user.id),
        email=user.email,
        nome=tec.nome or user.name,
        whatsapp=tec.whatsapp or user.whatsapp,
        role=user.role.value,
        foto_b64=user.foto_b64,
        ativo=tec.ativo,
        last_gps_ts=tec.gps_ts.isoformat() if tec.gps_ts else None,
        estatisticas=PerfilEstatisticas(
            os_pendentes=int(pendentes or 0),
            os_em_andamento=int(em_andamento or 0),
            os_concluidas_mes=int(concluidas_mes or 0),
            csat_avg_mes=round(float(csat_avg), 2) if csat_avg is not None else None,
        ),
    )


@router.post(
    "/foto",
    response_model=PerfilOut,
    dependencies=[_role_dep],
)
async def upload_foto_perfil(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    tec: Annotated[Tecnico, Depends(current_tecnico)],
    file: Annotated[UploadFile, File()],
) -> PerfilOut:
    """Upload foto de perfil. Max 5MB no upload, redimensiona pra 256x256."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="arquivo deve ser imagem")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="imagem excede 5MB")
    try:
        b64 = _processar_foto(raw)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"imagem invalida: {e}"
        ) from e
    user.foto_b64 = b64
    await session.flush()
    return await get_perfil(session=session, user=user, tec=tec)


@router.delete(
    "/foto",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def remover_foto_perfil(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    user.foto_b64 = None
    await session.flush()


@router.post(
    "/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def mudar_senha(
    body: MudarSenhaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Tecnico muda a propria senha. Exige senha atual valida."""
    import structlog

    from ondeline_api.auth.passwords import hash_password, verify_password

    log = structlog.get_logger(__name__)
    if not verify_password(body.senha_atual, user.password_hash):
        log.warning("user.mudar_senha.atual_invalida", user_id=str(user.id))
        raise HTTPException(status_code=401, detail="senha atual incorreta")
    if body.senha_nova == body.senha_atual:
        raise HTTPException(
            status_code=422, detail="senha nova deve ser diferente da atual"
        )
    user.password_hash = hash_password(body.senha_nova)
    await session.flush()
    log.info("user.mudar_senha.ok", user_id=str(user.id))
