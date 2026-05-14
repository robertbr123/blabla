"""GET/POST/PATCH/DELETE /api/v1/os* — Ordens de Servico."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.os import (
    OsConcluirIn,
    OsCreate,
    OsDeleteOut,
    OsListItem,
    OsOut,
    OsPatch,
    OsReatribuirIn,
)
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.business import ConversaEstado, OsStatus
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo

router = APIRouter(prefix="/api/v1/os", tags=["ordens-servico"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_admin_dep = Depends(require_role(Role.ADMIN))

# Storage path for photos. In production this should be a configured volume.
FOTOS_DIR = Path("/tmp/ondeline_os_fotos")

FOLLOWUP_MSG = (
    "Olá! 👋 O técnico concluiu o atendimento. O serviço ficou ok para você? "
    "Responda *SIM* se tudo resolveu ou *NÃO* se ainda há problema."
)

log = structlog.get_logger(__name__)


async def _send_whatsapp(whatsapp: str, msg: str) -> None:
    """Best-effort WhatsApp notification. Never raises."""
    try:
        from ondeline_api.adapters.evolution import EvolutionAdapter
        from ondeline_api.config import get_settings

        s = get_settings()
        evo = EvolutionAdapter(
            base_url=s.evolution_url,
            instance=s.evolution_instance,
            api_key=s.evolution_key,
        )
        try:
            await evo.send_text(whatsapp, msg)
        except Exception:
            log.warning("os.whatsapp_send_failed", whatsapp=whatsapp, exc_info=True)
        finally:
            await evo.aclose()
    except Exception:
        log.warning("os.whatsapp_send_failed_cleanup", whatsapp=whatsapp)


@router.get("", response_model=CursorPage[OsListItem], dependencies=[_role_dep])
async def list_os(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tecnico: Annotated[UUID | None, Query()] = None,
    cliente_id: Annotated[UUID | None, Query()] = None,
) -> CursorPage[OsListItem]:
    repo = OrdemServicoRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        tecnico_id=tecnico,
        cliente_id=cliente_id,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = [OsListItem.model_validate(o) for o in rows]
    return CursorPage[OsListItem](
        items=items,
        next_cursor=encode_cursor(next_cur) if next_cur else None,
    )


@router.post(
    "", response_model=OsOut, status_code=status.HTTP_201_CREATED, dependencies=[_role_dep]
)
async def create_os(
    body: OsCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    tecnico = await TecnicoRepo(session).get_by_id(body.tecnico_id)
    if tecnico is None:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    if not tecnico.ativo:
        raise HTTPException(status_code=422, detail="Técnico inativo")
    codigo = await next_codigo(session)
    os_ = await repo.create(
        codigo=codigo,
        cliente_id=body.cliente_id,
        tecnico_id=body.tecnico_id,
        problema=body.problema,
        endereco=body.endereco,
    )
    if body.agendamento_at:
        os_.agendamento_at = body.agendamento_at
        await session.flush()
    if tecnico.whatsapp:
        from sqlalchemy import select

        from ondeline_api.db.crypto import decrypt_pii
        from ondeline_api.db.models.business import Cliente

        cliente_row = (
            await session.execute(select(Cliente).where(Cliente.id == body.cliente_id))
        ).scalar_one_or_none()
        nome_cliente = (
            decrypt_pii(cliente_row.nome_encrypted) if cliente_row else "Cliente"
        )
        msg = (
            f"Nova OS {codigo}\n"
            f"Cliente: {nome_cliente}\n"
            f"Endereço: {body.endereco}\n"
            f"Problema: {body.problema}"
        )
        await _send_whatsapp(tecnico.whatsapp, msg)
    return OsOut.model_validate(os_)


@router.get("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def get_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    return OsOut.model_validate(os_)


@router.patch("/{os_id}", response_model=OsOut, dependencies=[_role_dep])
async def patch_os(
    os_id: UUID,
    body: OsPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    await repo.update(
        os_,
        status=body.status,
        tecnico_id=body.tecnico_id,
        agendamento_at=body.agendamento_at,
    )
    return OsOut.model_validate(os_)


@router.post("/{os_id}/reatribuir", response_model=OsOut, dependencies=[_role_dep])
async def reatribuir_os(
    os_id: UUID,
    body: OsReatribuirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if os_.status == OsStatus.CONCLUIDA:
        raise HTTPException(
            status_code=422, detail="OS concluída não pode ser reatribuída"
        )
    if os_.tecnico_id == body.tecnico_id:
        return OsOut.model_validate(os_)

    tec_repo = TecnicoRepo(session)
    novo_tec = await tec_repo.get_by_id(body.tecnico_id)
    if novo_tec is None:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")
    if not novo_tec.ativo:
        raise HTTPException(
            status_code=422, detail="Técnico inativo não pode receber OS"
        )

    old_tecnico_id = os_.tecnico_id
    old_tec = await tec_repo.get_by_id(old_tecnico_id) if old_tecnico_id else None

    historico = list(os_.historico_reatribuicoes or [])
    historico.append(
        {
            "de": str(old_tecnico_id) if old_tecnico_id else None,
            "para": str(body.tecnico_id),
            "em": datetime.now(tz=UTC).isoformat(),
            "por": str(current_user.id),
        }
    )
    os_.tecnico_id = body.tecnico_id
    os_.reatribuido_em = datetime.now(tz=UTC)
    os_.reatribuido_por = current_user.id
    os_.historico_reatribuicoes = historico
    await session.flush()

    if old_tec and old_tec.whatsapp:
        await _send_whatsapp(
            old_tec.whatsapp,
            f"A OS {os_.codigo} foi reatribuída para outro técnico. Obrigado!",
        )
    if novo_tec.whatsapp:
        msg = (
            f"OS reatribuída para você: {os_.codigo}\n"
            f"Endereço: {os_.endereco}\n"
            f"Problema: {os_.problema}"
        )
        await _send_whatsapp(novo_tec.whatsapp, msg)

    return OsOut.model_validate(os_)


@router.delete("/{os_id}", response_model=OsDeleteOut, dependencies=[_admin_dep])
async def delete_os(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsDeleteOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    notif_sent = False
    if os_.tecnico_id:
        tec = await TecnicoRepo(session).get_by_id(os_.tecnico_id)
        if tec and tec.whatsapp:
            await _send_whatsapp(
                tec.whatsapp,
                f"A OS {os_.codigo} foi cancelada no sistema.",
            )
            notif_sent = True

    await session.delete(os_)
    await session.flush()
    return OsDeleteOut(notif_tecnico=notif_sent)


@router.post(
    "/{os_id}/foto",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def upload_foto(
    os_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
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


@router.post(
    "/{os_id}/concluir",
    response_model=OsOut,
    dependencies=[_role_dep],
)
async def concluir_os(
    os_id: UUID,
    body: OsConcluirIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OsOut:
    repo = OrdemServicoRepo(session)
    os_ = await repo.get_by_id(os_id)
    if os_ is None:
        raise HTTPException(status_code=404, detail="OS not found")
    if os_.status == OsStatus.CONCLUIDA:
        raise HTTPException(status_code=422, detail="OS já concluída")
    await repo.concluir(os_, csat=body.csat, comentario=body.comentario)

    if os_.cliente_id:
        conversa = await ConversaRepo(session).find_active_by_cliente_id(os_.cliente_id)
        if conversa:
            await _send_whatsapp(conversa.whatsapp, FOLLOWUP_MSG)
            conversa.estado = ConversaEstado.AGUARDA_FOLLOWUP_OS
            conversa.followup_os_id = os_.id
            await session.flush()

    return OsOut.model_validate(os_)
