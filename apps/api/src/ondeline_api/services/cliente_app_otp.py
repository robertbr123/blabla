"""OTP via WhatsApp para auth do app cliente.

- Gera codigo numerico 6 digitos.
- Persiste como hash + expires_at (10min).
- Manda via EvolutionAdapter (mesma instancia do bot).
- Verifica com tolerancia de 5 tentativas antes de invalidar.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.db.models.cliente_app import ClienteAppOtp

OTP_TTL_MIN = 10
OTP_MAX_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _to_jid(telefone: str) -> str:
    jid = _digits(telefone)
    if not jid.startswith("55"):
        jid = "55" + jid
    return jid + "@s.whatsapp.net"


async def issue(
    session: AsyncSession,
    *,
    cpf_hash: str,
    telefone: str,
    purpose: str,
    evolution: EvolutionAdapter,
) -> None:
    """Gera, persiste e envia OTP. Idempotente: invalida OTPs anteriores."""
    stmt = select(ClienteAppOtp).where(
        ClienteAppOtp.cpf_hash == cpf_hash,
        ClienteAppOtp.purpose == purpose,
        ClienteAppOtp.consumed_at.is_(None),
    )
    for old in (await session.execute(stmt)).scalars():
        old.consumed_at = datetime.now(UTC)

    code = f"{secrets.randbelow(1_000_000):06d}"
    otp = ClienteAppOtp(
        cpf_hash=cpf_hash,
        code_hash=_hash_code(code),
        purpose=purpose,
        expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MIN),
    )
    session.add(otp)
    await session.flush()

    await evolution.send_text(
        _to_jid(telefone),
        (
            f"Ondeline: seu codigo de acesso e *{code}*. "
            f"Valido por {OTP_TTL_MIN} minutos. "
            f"Se voce nao solicitou, ignore esta mensagem."
        ),
    )


class OtpInvalid(Exception):
    pass


class OtpExpired(OtpInvalid):
    pass


class OtpExhausted(OtpInvalid):
    pass


async def verify(session: AsyncSession, *, cpf_hash: str, code: str, purpose: str) -> None:
    stmt = (
        select(ClienteAppOtp)
        .where(
            ClienteAppOtp.cpf_hash == cpf_hash,
            ClienteAppOtp.purpose == purpose,
            ClienteAppOtp.consumed_at.is_(None),
        )
        .order_by(desc(ClienteAppOtp.created_at))
        .limit(1)
    )
    otp = (await session.execute(stmt)).scalar_one_or_none()
    if otp is None:
        raise OtpInvalid("no active otp")

    if otp.expires_at < datetime.now(UTC):
        otp.consumed_at = datetime.now(UTC)
        await session.flush()
        raise OtpExpired("otp expired")

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp.consumed_at = datetime.now(UTC)
        await session.flush()
        raise OtpExhausted("too many attempts")

    if otp.code_hash != _hash_code(code):
        otp.attempts += 1
        await session.flush()
        raise OtpInvalid("wrong code")

    otp.consumed_at = datetime.now(UTC)
    await session.flush()
