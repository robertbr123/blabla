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

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp import WhatsAppAdapter, WhatsAppError
from ondeline_api.db.models.cliente_app import ClienteAppOtp
from ondeline_api.observability.metrics import otp_send_total
from ondeline_api.services.whatsapp_message_log import extract_wamid, record_sent

log = structlog.get_logger(__name__)

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
    adapter: WhatsAppAdapter,
    template_name: str | None = None,
    fallback: WhatsAppAdapter | None = None,
) -> None:
    """Gera, persiste e envia OTP. Idempotente: invalida OTPs anteriores.

    Envio provider-aware:
    - ``template_name`` setado (canal Cloud): envia via TEMPLATE de
      autenticacao (``send_template`` com botao copiar-codigo). E a unica forma
      de mandar OTP pelo numero oficial fora da janela de 24h da Meta.
    - ``template_name`` None (canal Evolution): envia texto livre.

    Fallback: se o envio primario levantar ``WhatsAppError`` e houver
    ``fallback``, reenvia o MESMO codigo via texto livre (Evolution). Mantem o
    login funcionando se o Cloud estiver com problema. Erros que nao sejam
    ``WhatsAppError`` propagam (sao bugs, nao falha de provider).
    """
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

    jid = _to_jid(telefone)
    text = (
        f"Ondeline: seu codigo de acesso e *{code}*. "
        f"Valido por {OTP_TTL_MIN} minutos. "
        f"Se voce nao solicitou, ignore esta mensagem."
    )

    provider = "cloud" if template_name else "evolution"
    try:
        if template_name:
            send_result = await adapter.send_template(
                jid,
                name=template_name,
                language="pt_BR",
                body_params=[code],
                otp_code=code,
            )
            # Persiste pra metricas de template (Fase 2.2).
            await record_sent(
                session,
                wamid=extract_wamid(send_result),
                template_name=template_name,
                recipient_jid=jid,
            )
        else:
            await adapter.send_text(jid, text)
        otp_send_total.labels(provider=provider, result="success").inc()
    except WhatsAppError as e:
        if fallback is None:
            otp_send_total.labels(provider=provider, result="error").inc()
            raise
        log.warning(
            "otp.primary_send_failed_fallback",
            purpose=purpose,
            template=template_name,
            error=str(e),
        )
        try:
            await fallback.send_text(jid, text)
            otp_send_total.labels(
                provider=provider, result="fallback_to_evolution"
            ).inc()
        except WhatsAppError:
            # Fallback tambem falhou — pior cenario; conta como error.
            otp_send_total.labels(provider=provider, result="error").inc()
            raise


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
