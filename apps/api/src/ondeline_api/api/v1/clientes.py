"""GET/DELETE /api/v1/clientes — list, detail, LGPD export, LGPD delete."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.cliente import ClienteDetail, ClienteListItem
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    Mensagem,
    OrdemServico,
)
from ondeline_api.db.models.identity import Role
from ondeline_api.deps import get_db
from ondeline_api.repositories.cliente import ClienteRepo

router = APIRouter(prefix="/api/v1/clientes", tags=["clientes"])
_attendant_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_admin_dep = Depends(require_role(Role.ADMIN))


def _to_list_item(c: Cliente) -> ClienteListItem:
    return ClienteListItem.model_validate({
        "id": c.id,
        "whatsapp": c.whatsapp,
        "plano": c.plano,
        "status": c.status,
        "cidade": c.cidade,
        "sgp_provider": c.sgp_provider.value if c.sgp_provider else None,
        "sgp_id": c.sgp_id,
        "created_at": c.created_at,
        "last_seen_at": c.last_seen_at,
    })


def _to_detail(c: Cliente) -> ClienteDetail:
    nome = decrypt_pii(c.nome_encrypted) if c.nome_encrypted else ""
    cpf = decrypt_pii(c.cpf_cnpj_encrypted) if c.cpf_cnpj_encrypted else ""
    endereco = decrypt_pii(c.endereco_encrypted) if c.endereco_encrypted else None
    return ClienteDetail.model_validate({
        "id": c.id,
        "whatsapp": c.whatsapp,
        "plano": c.plano,
        "status": c.status,
        "cidade": c.cidade,
        "sgp_provider": c.sgp_provider.value if c.sgp_provider else None,
        "sgp_id": c.sgp_id,
        "created_at": c.created_at,
        "last_seen_at": c.last_seen_at,
        "nome": nome,
        "cpf_cnpj": cpf,
        "endereco": endereco,
        "retention_until": c.retention_until,
    })


@router.get("", response_model=CursorPage[ClienteListItem], dependencies=[_attendant_dep])
async def list_clientes(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    q: Annotated[str | None, Query()] = None,
    cidade: Annotated[str | None, Query()] = None,
) -> CursorPage[ClienteListItem]:
    repo = ClienteRepo(session)
    rows, next_cur = await repo.list_paginated(
        q=q, cidade=cidade, cursor=parse_cursor(cursor), limit=parse_limit(limit)
    )
    items = [_to_list_item(c) for c in rows]
    return CursorPage[ClienteListItem](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.get("/{cliente_id}", response_model=ClienteDetail, dependencies=[_attendant_dep])
async def get_cliente(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClienteDetail:
    repo = ClienteRepo(session)
    c = await repo.get_by_id(cliente_id)
    if c is None:
        raise HTTPException(status_code=404, detail="cliente not found")
    return _to_detail(c)


@router.get("/{cliente_id}/export", dependencies=[_admin_dep])
async def export_cliente(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    repo = ClienteRepo(session)
    c = await repo.get_by_id(cliente_id)
    if c is None:
        raise HTTPException(status_code=404, detail="cliente not found")

    cliente_data = _to_detail(c).model_dump(mode="json")

    # Collect conversas
    conv_stmt = select(Conversa).where(Conversa.cliente_id == c.id)
    conversas = list((await session.execute(conv_stmt)).scalars().all())
    conv_data = []
    for conv in conversas:
        msg_stmt = select(Mensagem).where(Mensagem.conversa_id == conv.id).order_by(Mensagem.created_at)
        msgs = list((await session.execute(msg_stmt)).scalars().all())
        conv_data.append({
            "id": str(conv.id),
            "whatsapp": conv.whatsapp,
            "estado": conv.estado.value,
            "status": conv.status.value,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "mensagens": [
                {
                    "id": str(m.id),
                    "role": m.role.value,
                    "content": decrypt_pii(m.content_encrypted) if m.content_encrypted else None,
                    "media_type": m.media_type,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        })

    # Collect OS
    os_stmt = select(OrdemServico).where(OrdemServico.cliente_id == c.id)
    oss = list((await session.execute(os_stmt)).scalars().all())
    os_data = [
        {
            "id": str(o.id),
            "codigo": o.codigo,
            "status": o.status.value,
            "problema": o.problema,
            "endereco": o.endereco,
            "criada_em": o.criada_em.isoformat() if o.criada_em else None,
            "concluida_em": o.concluida_em.isoformat() if o.concluida_em else None,
            "csat": o.csat,
        }
        for o in oss
    ]

    # Build zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("cliente.json", json.dumps(cliente_data, indent=2, default=str))
        zf.writestr("conversas.json", json.dumps(conv_data, indent=2))
        zf.writestr("ordens_servico.json", json.dumps(os_data, indent=2))
        zf.writestr(
            "README.txt",
            f"LGPD export para cliente {cliente_id}\n"
            f"Gerado em: {datetime.now(tz=UTC).isoformat()}\n"
            f"Contem: cliente.json, conversas.json, ordens_servico.json\n",
        )
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cliente-{cliente_id}.zip"'},
    )


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_admin_dep],
)
async def delete_cliente(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ClienteRepo(session)
    c = await repo.get_by_id(cliente_id)
    if c is None:
        raise HTTPException(status_code=404, detail="cliente not found")
    await repo.soft_delete(c)
