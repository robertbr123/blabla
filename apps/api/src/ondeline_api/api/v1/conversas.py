"""GET/POST /api/v1/conversas* — atendimento de conversas."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.conversa import (
    ClienteEmbutido,
    ConversaListItem,
    ConversaOut,
    ResponderIn,
    VincularClienteIn,
)
from ondeline_api.api.schemas.mensagem import MensagemOut
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente, ConversaEstado, Mensagem
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.cliente import ClienteRepo
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_attend import (
    ConversaNotFound,
    atender,
    encerrar,
)
from ondeline_api.services.responder import responder
from ondeline_api.workers.runtime import CeleryOutboundEnqueuer, get_redis

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas"])
_role_dep = Depends(require_role(Role.ATENDENTE, Role.ADMIN))


def _to_msg_out(m: Mensagem) -> MensagemOut:
    return MensagemOut(
        id=m.id,
        conversa_id=m.conversa_id,
        role=m.role.value,
        content=decrypt_pii(m.content_encrypted) if m.content_encrypted else None,
        media_type=m.media_type,
        media_url=m.media_url,
        created_at=m.created_at,
    )


@router.get("", response_model=CursorPage[ConversaListItem], dependencies=[_role_dep])
async def list_conversas(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query()] = None,
    canal_id: Annotated[UUID | None, Query()] = None,
) -> CursorPage[ConversaListItem]:
    repo = ConversaRepo(session)
    rows, next_cur = await repo.list_paginated(
        status=status_filter,
        q=q,
        canal_id=canal_id,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    items = []
    for conversa, nome_encrypted in rows:
        item = ConversaListItem.model_validate(conversa)
        if nome_encrypted:
            item.cliente_nome = decrypt_pii(nome_encrypted)
        items.append(item)
    return CursorPage[ConversaListItem](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.get("/{conversa_id}", response_model=ConversaOut, dependencies=[_role_dep])
async def get_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConversaOut:
    from sqlalchemy import select

    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    msgs, _ = await repo.list_messages(c.id, limit=50)
    out = ConversaOut.model_validate(c)
    out.mensagens = [_to_msg_out(m) for m in msgs]
    if c.resumo_handoff_encrypted:
        out.resumo_handoff = decrypt_pii(c.resumo_handoff_encrypted)
        out.resumo_handoff_at = c.resumo_handoff_at

    if c.cliente_id is not None:
        cliente_row = (
            await session.execute(select(Cliente).where(Cliente.id == c.cliente_id))
        ).scalar_one_or_none()
        if cliente_row is not None:
            out.cliente = ClienteEmbutido(
                id=cliente_row.id,
                nome=decrypt_pii(cliente_row.nome_encrypted) if cliente_row.nome_encrypted else "",
                cpf_cnpj=decrypt_pii(cliente_row.cpf_cnpj_encrypted) if cliente_row.cpf_cnpj_encrypted else "",
                whatsapp=cliente_row.whatsapp,
                plano=cliente_row.plano,
                cidade=cliente_row.cidade,
                endereco=decrypt_pii(cliente_row.endereco_encrypted) if cliente_row.endereco_encrypted else None,
            )
    return out


@router.get(
    "/{conversa_id}/mensagens",
    response_model=CursorPage[MensagemOut],
    dependencies=[_role_dep],
)
async def list_messages(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
) -> CursorPage[MensagemOut]:
    repo = ConversaRepo(session)
    msgs, next_cur = await repo.list_messages(
        conversa_id, cursor=parse_cursor(cursor), limit=parse_limit(limit)
    )
    items = [_to_msg_out(m) for m in msgs]
    return CursorPage[MensagemOut](
        items=items, next_cursor=encode_cursor(next_cur) if next_cur else None
    )


@router.post(
    "/{conversa_id}/atender",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def atender_endpoint(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        await atender(session, conversa_id, user.id)
    except ConversaNotFound as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


@router.post(
    "/{conversa_id}/responder",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def responder_endpoint(
    conversa_id: UUID,
    body: ResponderIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    enqueuer = CeleryOutboundEnqueuer()
    redis = await get_redis()
    try:
        await responder(session, conversa_id, user.id, body.text, enqueuer, redis=redis)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


_ESTADOS_PRE_IDENT = {
    ConversaEstado.INICIO,
    ConversaEstado.AGUARDA_OPCAO,
    ConversaEstado.CLIENTE_CPF,
    ConversaEstado.LEAD_NOME,
    ConversaEstado.LEAD_INTERESSE,
}


@router.post(
    "/{conversa_id}/vincular-cliente",
    response_model=ConversaOut,
    dependencies=[_role_dep],
)
async def vincular_cliente_endpoint(
    conversa_id: UUID,
    body: VincularClienteIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ConversaOut:
    """Vincula manualmente um cliente (via CPF/CNPJ) a uma conversa.

    Util quando o cliente digitou CPF errado no chat e o bot nao conseguiu
    identifica-lo. Faz lookup no SGP, upsert no DB local e libera o gate
    F12 movendo o estado pra CLIENTE.
    """
    import structlog

    from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
    from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
    from ondeline_api.adapters.sgp.router import SgpRouter
    from ondeline_api.config import get_settings
    from ondeline_api.services.sgp_cache import SgpCacheService
    from ondeline_api.services.sgp_config import load_sgp_config
    from ondeline_api.workers.runtime import get_redis

    log = structlog.get_logger(__name__)

    repo = ConversaRepo(session)
    conversa = await repo.get_by_id(conversa_id)
    if conversa is None:
        raise HTTPException(status_code=404, detail="conversa not found")

    cpf_digits = "".join(c for c in body.cpf if c.isdigit())
    if len(cpf_digits) not in (11, 14):
        raise HTTPException(status_code=400, detail="CPF/CNPJ invalido")

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
    # Invalida cache negativo: se o atendente esta vinculando manualmente,
    # provavelmente houve erro previo (CPF digitado errado, ou bug do _format_endereco).
    await cache.invalidate(cpf_digits)
    cli_sgp = await cache.get_cliente(cpf_digits)
    if cli_sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado no SGP")

    cliente_db = await ClienteRepo(session).upsert_from_sgp(
        cli_sgp, whatsapp=conversa.whatsapp
    )
    conversa.cliente_id = cliente_db.id
    if conversa.estado in _ESTADOS_PRE_IDENT:
        conversa.estado = ConversaEstado.CLIENTE
    await session.flush()

    log.info(
        "conversa.vincular_cliente",
        conversa_id=str(conversa_id),
        cliente_id=str(cliente_db.id),
        atendente_id=str(user.id),
        cpf=cpf_digits,
    )

    # Retorna conversa atualizada (mesmo shape que GET).
    msgs, _ = await repo.list_messages(conversa.id, limit=50)
    out = ConversaOut.model_validate(conversa)
    out.mensagens = [_to_msg_out(m) for m in msgs]
    out.cliente = ClienteEmbutido(
        id=cliente_db.id,
        nome=decrypt_pii(cliente_db.nome_encrypted) if cliente_db.nome_encrypted else "",
        cpf_cnpj=decrypt_pii(cliente_db.cpf_cnpj_encrypted) if cliente_db.cpf_cnpj_encrypted else "",
        whatsapp=cliente_db.whatsapp,
        plano=cliente_db.plano,
        cidade=cliente_db.cidade,
        endereco=decrypt_pii(cliente_db.endereco_encrypted) if cliente_db.endereco_encrypted else None,
    )
    return out


@router.post(
    "/{conversa_id}/encerrar",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def encerrar_endpoint(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await encerrar(session, conversa_id)
    except ConversaNotFound as exc:
        raise HTTPException(status_code=404, detail="conversa not found") from exc


@router.delete(
    "/{conversa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_dep],
)
async def delete_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    await repo.soft_delete(c)
