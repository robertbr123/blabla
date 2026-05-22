"""Router /api/v1/cliente-app/* — endpoints de me, plano e avisos.

Todos exigem token cliente (kind=cliente). Reaproveita SgpCacheService
ja existente do dashboard.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.api.schemas.cliente_app_auth import (
    AvisosOut,
    BoletoUrlOut,
    ChangePasswordIn,
    ContratoOut,
    EnderecoOut,
    FaturaOut,
    FaturasOut,
    MeOut,
    PixOut,
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
    # Local pode ter vindo vazio em registros criados em versoes antigas
    # com bugs de parse SGP. Fallback no SGP atual.
    nome_local = decrypt_pii(user.nome_encrypted) if user.nome_encrypted else ""
    nome = nome_local.strip() or (sgp.nome if sgp else "") or ""
    tel_local = decrypt_pii(user.telefone_encrypted) if user.telefone_encrypted else ""
    telefone = tel_local.strip() or (sgp.whatsapp if sgp else "") or ""
    return MeOut(
        id=str(user.id),
        nome=nome,
        cpf_last4=user.cpf_last4,
        telefone=telefone,
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


def _fatura_out(f: Fatura) -> FaturaOut:
    return FaturaOut(
        id=f.id,
        valor=float(f.valor),
        vencimento=f.vencimento,
        status=f.status,
        dias_atraso=int(f.dias_atraso),
        tem_pdf=bool(f.link_pdf),
        tem_pix=bool(f.codigo_pix),
    )


@router.get("/faturas", response_model=FaturasOut)
async def faturas(
    status: str | None = None,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> FaturasOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        return FaturasOut(items=[])
    titulos = list(sgp.titulos)
    if status == "abertas":
        titulos = [t for t in titulos if t.status == "aberto"]
    elif status == "pagas":
        titulos = [t for t in titulos if t.status != "aberto"]
    titulos.sort(key=lambda t: t.vencimento, reverse=True)
    return FaturasOut(items=[_fatura_out(t) for t in titulos])


@router.get("/faturas/{titulo_id}/pix", response_model=PixOut)
async def fatura_pix(
    titulo_id: str,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> PixOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    for t in sgp.titulos:
        if t.id == titulo_id:
            if not t.codigo_pix:
                raise HTTPException(status_code=404, detail="fatura sem pix")
            return PixOut(codigo=t.codigo_pix)
    raise HTTPException(status_code=404, detail="fatura nao encontrada")


@router.get("/faturas/{titulo_id}/boleto", response_model=BoletoUrlOut)
async def fatura_boleto(
    titulo_id: str,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> BoletoUrlOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(status_code=404, detail="cliente nao encontrado")
    for t in sgp.titulos:
        if t.id == titulo_id:
            if not t.link_pdf:
                raise HTTPException(status_code=404, detail="fatura sem pdf")
            return BoletoUrlOut(url=t.link_pdf)
    raise HTTPException(status_code=404, detail="fatura nao encontrada")


@router.delete("/me", status_code=204)
async def delete_me(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """LGPD — anonimiza o registro do cliente.

    Mantemos a linha pra preservar FKs (cliente_app_os.cliente_app_user_id,
    cliente_app_messages, etc) mas zeramos PII. Substituimos cpf_hash por
    um marker unico pra liberar o indice de unicidade.
    """
    marker = f"deleted-{user.id}"
    user.cpf_hash = marker
    user.cpf_last4 = "0000"
    user.cpf_encrypted = encrypt_pii(marker)
    user.nome_encrypted = encrypt_pii("[conta excluida]")
    user.telefone_encrypted = encrypt_pii("")
    user.email_encrypted = None
    user.password_hash = None
    user.push_token = None
    user.biometric_enabled = False
    user.sgp_id = None
    user.status = "deleted"
    await session.flush()
    await session.commit()


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
