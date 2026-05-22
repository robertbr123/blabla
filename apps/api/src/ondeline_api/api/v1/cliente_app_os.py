"""Router /api/v1/cliente-app/os — abertura e listagem de chamados pelo cliente."""
from __future__ import annotations

import structlog
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.api.schemas.cliente_app_auth import (
    OsCreateIn,
    OsListOut,
    OsOut,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppOs, ClienteAppUser
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/cliente-app/os", tags=["cliente-app:os"])


def _os_out(o: ClienteAppOs) -> OsOut:
    return OsOut(
        id=str(o.id),
        tipo=o.tipo,
        descricao=o.descricao,
        status=o.status,
        created_at=o.created_at.isoformat(),
        updated_at=o.updated_at.isoformat(),
    )


@router.get("", response_model=OsListOut)
async def listar(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsListOut:
    stmt = (
        select(ClienteAppOs)
        .where(ClienteAppOs.cliente_app_user_id == user.id)
        .order_by(desc(ClienteAppOs.created_at))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return OsListOut(items=[_os_out(r) for r in rows])


def _to_jid(num: str) -> str:
    digits = "".join(c for c in num if c.isdigit())
    if not digits.startswith("55"):
        digits = "55" + digits
    return digits + "@s.whatsapp.net"


_TIPO_LABEL = {
    "sem_internet": "Sem internet",
    "mudanca_endereco": "Mudanca de endereco",
    "troca_plano": "Troca de plano",
}


async def _notify_admins(os_row: ClienteAppOs, user: ClienteAppUser) -> None:
    """Best-effort: notifica admins via WhatsApp. Nunca propaga erro."""
    s = get_settings()
    raw = (s.cliente_app_admin_notify or "").strip()
    if not raw:
        return
    destinos = [n.strip() for n in raw.split(",") if n.strip()]
    if not destinos:
        return

    nome = decrypt_pii(user.nome_encrypted) if user.nome_encrypted else "(sem nome)"
    telefone = decrypt_pii(user.telefone_encrypted) if user.telefone_encrypted else ""
    tipo_label = _TIPO_LABEL.get(os_row.tipo, os_row.tipo)
    desc_corta = os_row.descricao[:200] + ("..." if len(os_row.descricao) > 200 else "")
    msg = (
        f"*Novo chamado do app cliente*\n\n"
        f"*Tipo:* {tipo_label}\n"
        f"*Cliente:* {nome}\n"
        f"*Telefone:* {telefone}\n"
        f"*CPF:* ***.***.***-{user.cpf_last4}\n\n"
        f"*Descricao:*\n{desc_corta}"
    )

    evo = EvolutionAdapter(
        base_url=s.evolution_url,
        instance=s.evolution_instance,
        api_key=s.evolution_key,
    )
    try:
        for d in destinos:
            try:
                await evo.send_text(_to_jid(d), msg)
            except Exception:
                log.warning("cliente_app_os.notify_failed", destino=d, exc_info=True)
    finally:
        await evo.aclose()


@router.post("", response_model=OsOut, status_code=201)
async def criar(
    body: OsCreateIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsOut:
    os_row = ClienteAppOs(
        cliente_app_user_id=user.id,
        tipo=body.tipo,
        descricao=body.descricao,
        payload_json=body.payload,
        status="aberto",
    )
    session.add(os_row)
    await session.flush()
    await session.commit()
    await session.refresh(os_row)

    # Notifica admins (best-effort, nao bloqueia resposta em falha)
    try:
        await _notify_admins(os_row, user)
    except Exception:
        log.warning("cliente_app_os.notify_unexpected_error", exc_info=True)

    return _os_out(os_row)


@router.get("/{os_id}", response_model=OsOut)
async def detalhe(
    os_id: UUID,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> OsOut:
    row = await session.get(ClienteAppOs, os_id)
    if row is None or row.cliente_app_user_id != user.id:
        raise HTTPException(status_code=404, detail="chamado nao encontrado")
    return _os_out(row)
