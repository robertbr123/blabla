"""GET/POST /api/v1/conversas* — atendimento de conversas."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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


_MEDIA_DIR = Path("/tmp/ondeline_conversa_media")
_MAX_MEDIA_BYTES = 10 * 1024 * 1024  # 10 MB


def _classify_media(content_type: str) -> str | None:
    """Mapeia mimetype -> mediatype da Evolution. None se nao permitido."""
    ct = content_type.lower()
    if ct.startswith("image/"):
        return "image"
    if ct == "application/pdf" or ct.startswith("application/"):
        return "document"
    if ct.startswith("audio/"):
        return "audio"
    if ct.startswith("video/"):
        return "video"
    return None


@router.post(
    "/{conversa_id}/enviar-midia",
    response_model=MensagemOut,
    dependencies=[_role_dep],
)
async def enviar_midia_endpoint(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
    caption: Annotated[str, Form()] = "",
) -> MensagemOut:
    """Atendente envia midia (imagem, PDF, audio, video) para a conversa.

    Limites: 10MB. Tipos: image/*, application/pdf, audio/*, video/*.
    Salva localmente em /tmp/ondeline_conversa_media/{conversa_id}/<uuid>.<ext>
    e envia inline via Evolution. Registra Mensagem(role=atendente).
    """
    from datetime import UTC, datetime

    import structlog

    from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
    from ondeline_api.config import get_settings
    from ondeline_api.db.crypto import encrypt_pii
    from ondeline_api.db.models.business import MensagemRole
    from ondeline_api.services.conversa_events import publish as publish_event

    log = structlog.get_logger(__name__)

    repo = ConversaRepo(session)
    conversa = await repo.get_by_id(conversa_id)
    if conversa is None:
        raise HTTPException(status_code=404, detail="conversa not found")

    if not file.content_type:
        raise HTTPException(status_code=400, detail="content-type ausente")

    mediatype = _classify_media(file.content_type)
    if mediatype is None:
        raise HTTPException(
            status_code=400, detail=f"tipo nao suportado: {file.content_type}"
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="arquivo vazio")
    if len(contents) > _MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="arquivo excede 10MB")

    target_dir = _MEDIA_DIR / str(conversa_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix or ""
    fname = f"{uuid4().hex}{suffix}"
    fpath = target_dir / fname
    fpath.write_bytes(contents)
    fpath.chmod(0o600)

    s = get_settings()
    evolution = EvolutionAdapter(
        base_url=s.evolution_url,
        instance=s.evolution_instance,
        api_key=s.evolution_key,
    )
    try:
        await evolution.send_media_bytes(
            conversa.whatsapp,
            data=contents,
            mediatype=mediatype,
            mimetype=file.content_type,
            file_name=file.filename or fname,
            caption=caption or "",
        )
    except EvolutionError as exc:
        log.warning(
            "conversa.enviar_midia.evolution_failed",
            conversa_id=str(conversa_id),
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Evolution: {exc}") from exc
    finally:
        await evolution.aclose()

    # Registra mensagem (apos envio ok).
    if conversa.first_response_at is None:
        conversa.first_response_at = datetime.now(tz=UTC)

    msg = Mensagem(
        conversa_id=conversa.id,
        external_id=None,
        role=MensagemRole.ATENDENTE,
        content_encrypted=encrypt_pii(caption) if caption else None,
        media_type=file.content_type,
        media_url=str(fpath),
    )
    session.add(msg)
    await session.flush()

    log.info(
        "conversa.enviar_midia.ok",
        conversa_id=str(conversa_id),
        atendente_id=str(user.id),
        mediatype=mediatype,
        size=len(contents),
    )

    # SSE
    try:
        redis = await get_redis()
        await publish_event(
            redis,
            conversa.id,
            {
                "type": "msg",
                "id": str(msg.id),
                "role": "atendente",
                "text": caption or f"[{mediatype}]",
                "ts": msg.created_at.isoformat() if msg.created_at else None,
            },
        )
    except Exception:
        pass

    return _to_msg_out(msg)


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
