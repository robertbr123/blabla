"""Repositorio para ClienteAppUser."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser


def _cpf_clean(cpf: str) -> str:
    return "".join(c for c in cpf if c.isdigit())


async def get_by_cpf_hash(session: AsyncSession, cpf_hash: str) -> ClienteAppUser | None:
    stmt = select(ClienteAppUser).where(ClienteAppUser.cpf_hash == cpf_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID) -> ClienteAppUser | None:
    return await session.get(ClienteAppUser, user_id)


async def create_pending(
    session: AsyncSession,
    *,
    cpf: str,
    nome: str,
    telefone: str,
    sgp_id: str | None,
    email: str | None = None,
) -> ClienteAppUser:
    cpf_digits = _cpf_clean(cpf)
    if len(cpf_digits) != 11:
        raise ValueError("CPF must have 11 digits")
    user = ClienteAppUser(
        cpf_hash=hash_pii(cpf_digits),
        cpf_last4=cpf_digits[-4:],
        cpf_encrypted=encrypt_pii(cpf_digits),
        nome_encrypted=encrypt_pii(nome),
        telefone_encrypted=encrypt_pii(telefone),
        email_encrypted=encrypt_pii(email) if email else None,
        sgp_id=sgp_id,
        status="pending_otp",
    )
    session.add(user)
    await session.flush()
    return user


async def set_password(session: AsyncSession, user: ClienteAppUser, password_hash: str) -> None:
    user.password_hash = password_hash
    user.status = "active"
    await session.flush()


async def mark_login(session: AsyncSession, user: ClienteAppUser) -> None:
    user.last_login_at = datetime.now(UTC)
    await session.flush()
