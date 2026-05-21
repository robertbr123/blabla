"""Router /api/v1/cliente-app/auth/* — registro, OTP, login.

Setup token: JWT curto (10min) entre `register/verify` e `register/password`
para evitar criar usuario sem senha em estado pendente persistido.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.api.schemas.cliente_app_auth import (
    ForgotIn,
    LoginIn,
    RegisterPasswordIn,
    RegisterStartIn,
    RegisterStartOut,
    RegisterVerifyIn,
    RegisterVerifyOut,
    TokenOut,
)
from ondeline_api.api.webhook import limiter
from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.jwt import CLIENTE_ACCESS_TTL_DAYS
from ondeline_api.auth.passwords import hash_password, verify_password
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.deps import get_db
from ondeline_api.repositories import cliente_app_user as repo
from ondeline_api.services import cliente_app_otp as otp_svc

router = APIRouter(prefix="/api/v1/cliente-app/auth", tags=["cliente-app:auth"])

SETUP_TTL_MIN = 10
_RL_OTP = "5/hour"
_RL_AUTH = "10/hour"


def _evolution() -> EvolutionAdapter:
    s = get_settings()
    return EvolutionAdapter(
        base_url=s.evolution_url,
        instance=s.evolution_instance,
        api_key=s.evolution_key,
    )


async def _sgp_lookup_by_cpf(session: AsyncSession, cpf: str) -> ClienteSgp | None:
    """Busca cliente no SGP usando o cache compartilhado. None se nao existir."""
    from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
    from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
    from ondeline_api.adapters.sgp.router import SgpRouter
    from ondeline_api.services.sgp_cache import SgpCacheService
    from ondeline_api.services.sgp_config import load_sgp_config
    from ondeline_api.workers.runtime import get_redis

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
    return await cache.get_cliente(cpf)


def _setup_token(cpf_hash: str) -> str:
    secret = get_settings().jwt_secret.get_secret_value()
    iat = datetime.now(UTC)
    payload = {
        "cpf_hash": cpf_hash,
        "purpose": "register_setup",
        "iat": int(iat.timestamp()),
        "exp": int((iat + timedelta(minutes=SETUP_TTL_MIN)).timestamp()),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _decode_setup(token: str) -> dict[str, Any]:
    secret = get_settings().jwt_secret.get_secret_value()
    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="setup token expired") from None
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=400, detail="invalid setup token") from None
    if payload.get("purpose") != "register_setup":
        raise HTTPException(status_code=400, detail="invalid setup purpose")
    return payload


def _mask_phone(telefone: str) -> str:
    digits = "".join(c for c in telefone if c.isdigit())
    if len(digits) < 4:
        return "****"
    return f"****-{digits[-4:]}"


def _cliente_access_seconds() -> int:
    return CLIENTE_ACCESS_TTL_DAYS * 86400


@router.post("/register/start", response_model=RegisterStartOut)
@limiter.limit(_RL_OTP)
async def register_start(
    request: Request,
    response: Response,
    body: RegisterStartIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> RegisterStartOut:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)

    if user and user.status == "active":
        # Ja cadastrado — direciona pra /forgot
        raise HTTPException(status_code=409, detail="usuario ja cadastrado")

    if user is None:
        sgp_cliente = await _sgp_lookup_by_cpf(session, body.cpf)
        if sgp_cliente is None:
            raise HTTPException(status_code=404, detail="cpf nao encontrado")
        nome = sgp_cliente.nome
        telefone = sgp_cliente.whatsapp
        sgp_id = sgp_cliente.sgp_id
        if not telefone:
            raise HTTPException(status_code=409, detail="cliente sem telefone cadastrado no SGP")
        user = await repo.create_pending(
            session,
            cpf=body.cpf,
            nome=nome,
            telefone=telefone,
            sgp_id=sgp_id,
        )
    else:
        telefone = decrypt_pii(user.telefone_encrypted)

    evolution = _evolution()
    try:
        await otp_svc.issue(
            session,
            cpf_hash=cpf_hash,
            telefone=telefone,
            purpose="register",
            evolution=evolution,
        )
    finally:
        await evolution.aclose()
    await session.commit()
    return RegisterStartOut(masked_phone=_mask_phone(telefone))


@router.post("/register/verify", response_model=RegisterVerifyOut)
@limiter.limit(_RL_AUTH)
async def register_verify(
    request: Request,
    response: Response,
    body: RegisterVerifyIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> RegisterVerifyOut:
    cpf_hash = hash_pii(body.cpf)
    try:
        await otp_svc.verify(session, cpf_hash=cpf_hash, code=body.code, purpose="register")
    except otp_svc.OtpExpired:
        await session.commit()
        raise HTTPException(status_code=400, detail="codigo expirado") from None
    except otp_svc.OtpExhausted:
        await session.commit()
        raise HTTPException(status_code=400, detail="muitas tentativas") from None
    except otp_svc.OtpInvalid:
        await session.commit()
        raise HTTPException(status_code=400, detail="codigo invalido") from None
    await session.commit()
    return RegisterVerifyOut(setup_token=_setup_token(cpf_hash))


@router.post("/register/password", response_model=TokenOut)
@limiter.limit(_RL_AUTH)
async def register_password(
    request: Request,
    response: Response,
    body: RegisterPasswordIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenOut:
    payload = _decode_setup(body.setup_token)
    cpf_hash = payload["cpf_hash"]
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    if user is None:
        raise HTTPException(status_code=400, detail="setup invalido")

    await repo.set_password(session, user, hash_password(body.password))
    await repo.mark_login(session, user)
    await session.commit()

    access = jwt_mod.encode_cliente_access_token(user.id)
    return TokenOut(access_token=access, expires_in_seconds=_cliente_access_seconds())


@router.post("/login", response_model=TokenOut)
@limiter.limit(_RL_AUTH)
async def login(
    request: Request,
    response: Response,
    body: LoginIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenOut:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    # Sempre rodar verify para evitar timing attack
    candidate_hash = (
        user.password_hash
        if (user and user.password_hash)
        else "$argon2id$v=19$m=65536,t=3,p=4$invalidsaltinvalid$invalidvalueinvalidvalue"
    )
    ok = verify_password(body.password, candidate_hash)
    if user is None or not user.password_hash or user.status != "active" or not ok:
        await session.commit()
        raise HTTPException(status_code=401, detail="credenciais invalidas")

    await repo.mark_login(session, user)
    await session.commit()
    access = jwt_mod.encode_cliente_access_token(user.id)
    return TokenOut(access_token=access, expires_in_seconds=_cliente_access_seconds())


@router.post("/forgot", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(_RL_OTP)
async def forgot(
    request: Request,
    response: Response,
    body: ForgotIn,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    cpf_hash = hash_pii(body.cpf)
    user = await repo.get_by_cpf_hash(session, cpf_hash)
    # Resposta sempre 202 — nao revela se CPF existe
    if user is not None and user.status == "active":
        telefone = decrypt_pii(user.telefone_encrypted)
        evolution = _evolution()
        try:
            await otp_svc.issue(
                session,
                cpf_hash=cpf_hash,
                telefone=telefone,
                purpose="reset_pwd",
                evolution=evolution,
            )
        finally:
            await evolution.aclose()
    await session.commit()
    return {"status": "ok"}
