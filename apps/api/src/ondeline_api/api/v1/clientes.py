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
from pydantic import BaseModel as _BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.cliente import ClienteDetail, ClienteListItem
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    Mensagem,
    OrdemServico,
)
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.cliente import ClienteRepo

router = APIRouter(prefix="/api/v1/clientes", tags=["clientes"])
_attendant_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_admin_dep = Depends(require_role(Role.ADMIN))


class SgpClienteOut(_BaseModel):
    nome: str
    cpf_cnpj: str
    plano: str | None
    status_contrato: str | None
    cidade: str | None
    endereco: str | None
    cliente_id: str | None  # UUID do cliente no nosso DB, se já existir
    pppoe_login: str
    pppoe_senha: str


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


@router.get("/sgp", response_model=SgpClienteOut)
async def sgp_lookup(
    cpf: Annotated[str, Query()],
    session: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SgpClienteOut:
    """Busca cliente no SGP por CPF/CNPJ para pré-preenchimento de OS."""
    from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
    from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
    from ondeline_api.adapters.sgp.router import SgpRouter
    from ondeline_api.services.sgp_cache import SgpCacheService
    from ondeline_api.services.sgp_config import load_sgp_config
    from ondeline_api.workers.runtime import get_redis
    from ondeline_api.config import get_settings

    s = get_settings()
    redis = await get_redis()
    sgp_ond = await load_sgp_config(session, "ondeline")
    sgp_lnk = await load_sgp_config(session, "linknetam")
    router_sgp = SgpRouter(
        primary=SgpOndelineProvider(**sgp_ond),
        secondary=SgpLinkNetAMProvider(**sgp_lnk),
    )
    cache = SgpCacheService(
        redis=redis,
        session=session,
        router=router_sgp,
        ttl_cliente=s.sgp_cache_ttl_cliente,
        ttl_negativo=s.sgp_cache_ttl_negativo,
    )
    cli = await cache.get_cliente(cpf)
    if cli is None:
        raise HTTPException(status_code=404, detail="cliente não encontrado no SGP")

    contrato = cli.contratos[0] if cli.contratos else None
    pppoe_login = contrato.pppoe_login if contrato else ""
    pppoe_senha = contrato.pppoe_senha if contrato else ""
    cidade = (contrato.cidade if contrato and contrato.cidade else None) or (
        cli.endereco.cidade if cli.endereco else None
    )
    endereco_str = (
        f"{cli.endereco.logradouro}, {cli.endereco.numero}"
        if cli.endereco and cli.endereco.logradouro
        else None
    )

    # Verifica se já existe no DB
    from ondeline_api.db.crypto import hash_pii
    from ondeline_api.db.models.business import Cliente as ClienteModel
    from sqlalchemy import select as sa_select
    cpf_digits = "".join(c for c in cpf if c.isdigit())
    cpf_hash = hash_pii(cpf_digits)
    db_cli = (
        await session.execute(
            sa_select(ClienteModel).where(
                ClienteModel.cpf_hash == cpf_hash,
                ClienteModel.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    return SgpClienteOut(
        nome=cli.nome,
        cpf_cnpj=cpf_digits,
        plano=contrato.plano if contrato else None,
        status_contrato=contrato.status if contrato else None,
        cidade=cidade,
        endereco=endereco_str,
        cliente_id=str(db_cli.id) if db_cli else None,
        pppoe_login=pppoe_login,
        pppoe_senha=pppoe_senha,
    )


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
