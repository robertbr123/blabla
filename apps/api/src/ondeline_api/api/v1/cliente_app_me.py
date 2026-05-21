"""Router /api/v1/cliente-app/* — endpoints de me, plano e avisos.

Todos exigem token cliente (kind=cliente). Reaproveita SgpCacheService
ja existente do dashboard.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.api.schemas.cliente_app_auth import (
    AvisosOut,
    ChangePasswordIn,
    ContratoOut,
    EnderecoOut,
    MeOut,
    PlanoOut,
    UpdateMeIn,
)
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.auth.passwords import hash_password, verify_password
from ondeline_api.db.crypto import decrypt_pii, encrypt_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db

router = APIRouter(prefix="/api/v1/cliente-app", tags=["cliente-app:me"])


async def _sgp_cliente(session: AsyncSession, cpf_encrypted: str) -> ClienteSgp | None:
    """Reaproveita _sgp_lookup_by_cpf do router de auth pra nao duplicar."""
    from ondeline_api.api.v1.cliente_app_auth import _sgp_lookup_by_cpf

    cpf = decrypt_pii(cpf_encrypted)
    return await _sgp_lookup_by_cpf(session, cpf)


def _endereco_out(e: object) -> EnderecoOut:
    return EnderecoOut(
        logradouro=getattr(e, "logradouro", "") or "",
        numero=getattr(e, "numero", "") or "",
        bairro=getattr(e, "bairro", "") or "",
        cidade=getattr(e, "cidade", "") or "",
        uf=getattr(e, "uf", "") or "",
        cep=getattr(e, "cep", "") or "",
    )


def _build_me(user: ClienteAppUser, sgp: ClienteSgp | None) -> MeOut:
    plano_nome = sgp.contratos[0].plano if (sgp and sgp.contratos) else None
    return MeOut(
        id=str(user.id),
        nome=decrypt_pii(user.nome_encrypted),
        cpf_last4=user.cpf_last4,
        telefone=decrypt_pii(user.telefone_encrypted),
        email=decrypt_pii(user.email_encrypted) if user.email_encrypted else None,
        biometric_enabled=user.biometric_enabled,
        plano_nome=plano_nome,
        status_conexao=None,
    )


@router.get("/me", response_model=MeOut)
async def me(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MeOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    return _build_me(user, sgp)


@router.get("/plano", response_model=PlanoOut)
async def plano(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PlanoOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado no SGP")

    contratos = [
        ContratoOut(
            id=c.id,
            plano=c.plano,
            status=c.status,
            cidade=c.cidade,
            endereco=_endereco_out(c.endereco),
        )
        for c in sgp.contratos
    ]
    return PlanoOut(
        nome_titular=sgp.nome,
        contratos=contratos,
        endereco_principal=_endereco_out(sgp.endereco),
    )


@router.get("/avisos", response_model=AvisosOut)
async def avisos(
    _user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
) -> AvisosOut:
    # Fase 7 adiciona tabela + admin posting. Por ora vazio.
    return AvisosOut(items=[])


@router.patch("/me", response_model=MeOut)
async def update_me(
    body: UpdateMeIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> MeOut:
    if body.telefone is not None:
        user.telefone_encrypted = encrypt_pii(body.telefone)
    if body.email is not None:
        user.email_encrypted = encrypt_pii(body.email) if body.email else None
    await session.flush()
    await session.commit()
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    return _build_me(user, sgp)


@router.post("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    if user.password_hash is None or not verify_password(
        body.current_password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="senha atual incorreta")
    user.password_hash = hash_password(body.new_password)
    await session.flush()
    await session.commit()
