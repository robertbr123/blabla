"""Endpoints CRUD pra clientes cadastrados em campo.

Cria/lista/edita registros da tabela `clientes_cadastro` (separada de
`clientes` que e cache do SGP). PII e encriptado em repouso (Fernet) +
hash com pepper pra busca por CPF.

Roles:
- TECNICO, ATENDENTE, ADMIN: GET, POST (criar)
- ATENDENTE, ADMIN: PATCH
- ADMIN: DELETE, sync-sgp
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.deps_v1 import CursorParam, LimitParam, parse_cursor, parse_limit
from ondeline_api.api.schemas.cliente_cadastro import (
    ClienteCampoIn,
    ClienteCampoListItem,
    ClienteCampoOut,
    ClienteCampoPatch,
    ImportBatchIn,
    ImportResult,
    SgpPlano,
    SgpPlanosOut,
    SyncSgpIn,
)
from ondeline_api.api.schemas.pagination import CursorPage, encode_cursor
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii, hash_pii
from ondeline_api.db.models.business import ClienteCadastro
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.cliente_cadastro import ClienteCadastroRepo
from ondeline_api.services.sgp_planos import listar_planos_sgp
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/clientes-campo", tags=["clientes-campo"])
_role_any = Depends(require_role(Role.TECNICO, Role.ATENDENTE, Role.ADMIN))
_role_atendente = Depends(require_role(Role.ATENDENTE, Role.ADMIN))
_role_admin = Depends(require_role(Role.ADMIN))


# ── Helpers ──────────────────────────────────────────────────


def _only_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _to_out(c: ClienteCadastro) -> ClienteCampoOut:
    """Desencripta PII pra DTO completo. Falha de decrypt vira string vazia."""
    def _dec(v: str | None) -> str | None:
        if not v:
            return None
        try:
            return decrypt_pii(v)
        except Exception:
            return None

    return ClienteCampoOut(
        id=c.id,
        cpf=_dec(c.cpf_encrypted) or "",
        nome=_dec(c.nome_encrypted) or "",
        dob=c.dob,
        telefone=_dec(c.telefone_encrypted) or "",
        cep=c.cep,
        address=c.address,
        number=c.number,
        complement=c.complement,
        neighborhood=c.neighborhood,
        city=c.city,
        state=c.state,
        plan_id=c.plan_id,
        plan_nome=c.plan_nome,
        pppoe_user=_dec(c.pppoe_user_encrypted),
        pppoe_pass=_dec(c.pppoe_pass_encrypted),
        due_date=c.due_date,
        installer_user_id=c.installer_user_id,
        installer_nome=c.installer_nome,
        serial=c.serial,
        contrato=c.contrato,
        observation=c.observation,
        latitude=float(c.latitude) if c.latitude is not None else None,
        longitude=float(c.longitude) if c.longitude is not None else None,
        location_accuracy=(
            float(c.location_accuracy) if c.location_accuracy is not None else None
        ),
        fotos=c.fotos,
        registration_date=c.registration_date,
        sgp_synced_at=c.sgp_synced_at,
        sgp_id=c.sgp_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _to_list_item(c: ClienteCadastro) -> ClienteCampoListItem:
    """Versao reduzida pra listas. So decrypta CPF + nome (rapido)."""
    def _dec(v: str | None) -> str:
        if not v:
            return ""
        try:
            return decrypt_pii(v)
        except Exception:
            return ""

    return ClienteCampoListItem(
        id=c.id,
        cpf=_dec(c.cpf_encrypted),
        nome=_dec(c.nome_encrypted),
        address=c.address,
        number=c.number,
        neighborhood=c.neighborhood,
        city=c.city,
        plan_nome=c.plan_nome,
        installer_nome=c.installer_nome,
        sgp_synced_at=c.sgp_synced_at,
        sgp_id=c.sgp_id,
        created_at=c.created_at,
    )


# ── List + busca ─────────────────────────────────────────────


@router.get(
    "",
    response_model=CursorPage[ClienteCampoListItem],
    dependencies=[_role_any],
)
async def list_clientes_campo(
    session: Annotated[AsyncSession, Depends(get_db)],
    cursor: CursorParam = None,
    limit: LimitParam = None,
    q: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    sgp_status: Annotated[
        str | None, Query(pattern="^(synced|pending)$")
    ] = None,
    installer_user_id: Annotated[UUID | None, Query()] = None,
) -> CursorPage[ClienteCampoListItem]:
    repo = ClienteCadastroRepo(session)
    rows, next_cur = await repo.list_paginated(
        q=q,
        city=city,
        sgp_status=sgp_status,
        installer_user_id=installer_user_id,
        cursor=parse_cursor(cursor),
        limit=parse_limit(limit),
    )
    return CursorPage[ClienteCampoListItem](
        items=[_to_list_item(c) for c in rows],
        next_cursor=encode_cursor(next_cur) if next_cur else None,
    )


@router.get(
    "/by-cpf/{cpf}",
    response_model=ClienteCampoOut,
    dependencies=[_role_any],
)
async def get_by_cpf(
    cpf: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClienteCampoOut:
    digits = _only_digits(cpf)
    if len(digits) not in (11, 14):
        raise HTTPException(status_code=400, detail="CPF/CNPJ invalido")
    c = await ClienteCadastroRepo(session).get_by_cpf_hash(hash_pii(digits))
    if c is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    return _to_out(c)


@router.get(
    "/{cliente_id}",
    response_model=ClienteCampoOut,
    dependencies=[_role_any],
)
async def get_cliente_campo(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClienteCampoOut:
    c = await ClienteCadastroRepo(session).get_by_id(cliente_id)
    if c is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    return _to_out(c)


@router.get(
    "/{cliente_id}/ordens-servico",
    dependencies=[_role_any],
)
async def get_historico_os(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, str | None]]:
    """Lista OS do mesmo CPF via JOIN com `clientes` (cache SGP)."""
    from sqlalchemy import select

    from ondeline_api.db.models.business import Cliente, OrdemServico

    c = await ClienteCadastroRepo(session).get_by_id(cliente_id)
    if c is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")

    # Acha o Cliente SGP correspondente pelo mesmo cpf_hash.
    sgp_cli = (
        await session.execute(
            select(Cliente).where(
                Cliente.cpf_hash == c.cpf_hash,
                Cliente.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if sgp_cli is None:
        return []

    rows = (
        await session.execute(
            select(OrdemServico)
            .where(OrdemServico.cliente_id == sgp_cli.id)
            .order_by(OrdemServico.criada_em.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id": str(o.id),
            "codigo": o.codigo,
            "status": o.status.value,
            "problema": o.problema,
            "criada_em": o.criada_em.isoformat() if o.criada_em else None,
            "concluida_em": o.concluida_em.isoformat() if o.concluida_em else None,
        }
        for o in rows
    ]


# ── Create / Update / Delete ────────────────────────────────


@router.post(
    "",
    response_model=ClienteCampoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_role_any],
)
async def create_cliente_campo(
    body: ClienteCampoIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ClienteCampoOut:
    """Cria cliente_cadastro. installer_user_id/nome = user logado.
    Materiais e fotos virao em endpoints separados (Fase 4)."""
    cpf_digits = _only_digits(body.cpf)
    if len(cpf_digits) not in (11, 14):
        raise HTTPException(status_code=400, detail="CPF/CNPJ invalido")
    tel_digits = _only_digits(body.telefone)
    if len(tel_digits) < 10:
        raise HTTPException(status_code=400, detail="telefone invalido")

    repo = ClienteCadastroRepo(session)
    cpf_hash = hash_pii(cpf_digits)
    if await repo.get_by_cpf_hash(cpf_hash) is not None:
        raise HTTPException(
            status_code=409,
            detail="ja existe um cliente cadastrado com esse CPF",
        )

    cliente = ClienteCadastro(
        cpf_hash=cpf_hash,
        cpf_encrypted=encrypt_pii(cpf_digits),
        nome_encrypted=encrypt_pii(body.nome.strip()),
        dob=body.dob,
        telefone_encrypted=encrypt_pii(tel_digits),
        cep=body.cep,
        address=body.address.strip(),
        number=body.number.strip(),
        complement=body.complement,
        neighborhood=body.neighborhood,
        city=body.city.strip(),
        state=(body.state or None) and body.state.upper(),
        plan_id=body.plan_id,
        plan_nome=body.plan_nome.strip(),
        pppoe_user_encrypted=encrypt_pii(body.pppoe_user) if body.pppoe_user else None,
        pppoe_pass_encrypted=encrypt_pii(body.pppoe_pass) if body.pppoe_pass else None,
        due_date=body.due_date,
        installer_user_id=user.id,
        installer_nome=user.name,
        serial=body.serial,
        contrato=body.contrato,
        observation=body.observation,
        latitude=body.latitude,
        longitude=body.longitude,
        location_accuracy=body.location_accuracy,
        registration_date=date.today(),
    )
    try:
        await repo.create(cliente)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="conflito de CPF") from exc
    return _to_out(cliente)


@router.patch(
    "/{cliente_id}",
    response_model=ClienteCampoOut,
    dependencies=[_role_any],
)
async def patch_cliente_campo(
    cliente_id: UUID,
    body: ClienteCampoPatch,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ClienteCampoOut:
    """Edicao parcial. CPF e dob nao podem mudar (cria novo registro pra isso).

    Tecnicos podem editar — mas regra de quem-pode-editar-o-quê e suave aqui:
    o frontend e responsavel por mostrar somente os campos permitidos.
    """
    repo = ClienteCadastroRepo(session)
    cliente = await repo.get_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")

    # Tecnico so pode editar o que ele criou
    if user.role == Role.TECNICO and cliente.installer_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="tecnico so pode editar cliente que ele cadastrou",
        )

    data = body.model_dump(exclude_unset=True)
    # Campos de PII reencriptados
    if "nome" in data:
        cliente.nome_encrypted = encrypt_pii(data.pop("nome").strip())
    if "telefone" in data:
        tel_digits = _only_digits(data.pop("telefone"))
        if len(tel_digits) < 10:
            raise HTTPException(status_code=400, detail="telefone invalido")
        cliente.telefone_encrypted = encrypt_pii(tel_digits)
    if "pppoe_user" in data:
        v = data.pop("pppoe_user")
        cliente.pppoe_user_encrypted = encrypt_pii(v) if v else None
    if "pppoe_pass" in data:
        v = data.pop("pppoe_pass")
        cliente.pppoe_pass_encrypted = encrypt_pii(v) if v else None
    # Demais campos: copiar direto
    for k, v in data.items():
        if k == "state" and v:
            v = v.upper()
        setattr(cliente, k, v)
    await session.flush()
    return _to_out(cliente)


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_role_admin],
)
async def delete_cliente_campo(
    cliente_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = ClienteCadastroRepo(session)
    cliente = await repo.get_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    cliente.deleted_at = datetime.now(tz=UTC)
    await session.flush()


# ── Sync SGP (manual) ───────────────────────────────────────


@router.post(
    "/{cliente_id}/sync-sgp",
    response_model=ClienteCampoOut,
    dependencies=[_role_admin],
)
async def marcar_sincronizado_sgp(
    cliente_id: UUID,
    body: SyncSgpIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClienteCampoOut:
    """Admin marca um cliente como ja enviado pro SGP (cola o sgp_id manualmente)."""
    repo = ClienteCadastroRepo(session)
    cliente = await repo.get_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    await repo.marcar_sincronizado(cliente, body.sgp_id.strip())
    return _to_out(cliente)


# ── Importacao MySQL ────────────────────────────────────────


@router.post(
    "/import",
    response_model=ImportResult,
    dependencies=[_role_admin],
)
async def import_batch_json(
    body: ImportBatchIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ImportResult:
    """Importa lote de clientes (JSON). Admin only.

    Body: rows[] no formato compativel com MySQL antigo (cpf, name, dob,
    phone, address, ..., installer texto livre, registration_date).

    - dedup por cpf_hash (UPDATE se ja existe)
    - dry_run: nao grava nada, so reporta o que faria
    - mark_as_synced: marca sgp_synced_at = registration_date (default true,
      porque clientes do MySQL antigo ja estao no SGP)
    """
    from ondeline_api.services.cliente_import import import_rows

    return await import_rows(
        session,
        body.rows,
        dry_run=body.dry_run,
        mark_as_synced=body.mark_as_synced,
    )


@router.post(
    "/import/csv",
    response_model=ImportResult,
    dependencies=[_role_admin],
)
async def import_batch_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    dry_run: Annotated[bool, Form()] = False,
    mark_as_synced: Annotated[bool, Form()] = True,
) -> ImportResult:
    """Importa CSV com header. Admin only.

    Colunas esperadas (mesmas do MySQL antigo): cpf, name, dob, phone,
    cep, address, number, complement, neighborhood, city, state, plan,
    pppoe_user, pppoe_pass, due_date, installer, serial, contrato,
    observation, latitude, longitude, location_accuracy, registration_date.

    Limite: 10 MB.
    """
    from ondeline_api.services.cliente_import import import_rows, parse_csv

    if not file.content_type or not file.content_type.startswith(
        ("text/csv", "application/csv", "application/vnd.ms-excel", "text/plain")
    ):
        # Aceita mesmo assim — alguns clientes mandam octet-stream.
        pass
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV excede 10MB")
    try:
        rows = parse_csv(content)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"erro parseando CSV: {e}"
        ) from e
    return await import_rows(
        session,
        rows,
        dry_run=dry_run,
        mark_as_synced=mark_as_synced,
    )


# ════════════════════════════════════════════════════════════
# SGP — endpoint paralelo: lista planos
# ════════════════════════════════════════════════════════════

sgp_router = APIRouter(prefix="/api/v1/sgp", tags=["sgp"])


@sgp_router.get(
    "/planos",
    response_model=SgpPlanosOut,
    dependencies=[Depends(require_role(Role.TECNICO, Role.ATENDENTE, Role.ADMIN))],
)
async def get_planos_sgp(
    session: Annotated[AsyncSession, Depends(get_db)],
    provider: Annotated[
        str, Query(pattern="^(ondeline|linknetam)$")
    ] = "ondeline",
) -> SgpPlanosOut:
    """Lista planos do SGP. Cache Redis 1h."""
    from typing import cast

    from ondeline_api.services.sgp_config import Provider

    redis = await get_redis()
    try:
        planos = await listar_planos_sgp(session, redis, cast(Provider, provider))
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502, detail=f"SGP indisponivel: {e}"
        ) from e
    return SgpPlanosOut(
        provider=provider,
        planos=[SgpPlano(**p) for p in planos],
    )
