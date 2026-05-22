"""Router /api/v1/cliente-app/* — endpoints de me, plano e avisos.

Todos exigem token cliente (kind=cliente). Reaproveita SgpCacheService
ja existente do dashboard.
"""
from __future__ import annotations

from datetime import UTC, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp, Fatura
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


def _calc_dias_atraso(vencimento_str: str, status: str, hoje: date) -> int:
    """Calcula dias_atraso autoritativo a partir de vencimento + hoje.

    Nao confia no campo `diasAtraso` do SGP — observamos casos onde ele
    retorna valor antigo (ex: 10) mesmo com vencimento futuro. Se o titulo
    nao esta aberto OU vence no futuro, dias_atraso = 0.
    """
    if status != "aberto":
        return 0
    try:
        venc = date.fromisoformat(vencimento_str)
    except (ValueError, TypeError):
        return 0
    delta = (hoje - venc).days
    return max(0, delta)


def _fatura_out(f: Fatura, hoje: date) -> FaturaOut:
    return FaturaOut(
        id=f.id,
        valor=float(f.valor),
        vencimento=f.vencimento,
        status=f.status,
        # Recalculado — ignora f.dias_atraso do SGP.
        dias_atraso=_calc_dias_atraso(f.vencimento, f.status, hoje),
        tem_pdf=bool(f.link_pdf),
        tem_pix=bool(f.codigo_pix),
    )


@router.get("/faturas", response_model=FaturasOut)
async def faturas(
    status: str | None = None,
    force: bool = False,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> FaturasOut:
    # Pull-to-refresh manda force=true → invalida cache pra pegar SGP fresco
    # (ex: depois que admin deu baixa no SGP, cache de 1h ainda mostrava
    # como em aberto). User explicito > performance.
    if force:
        cpf = decrypt_pii(user.cpf_encrypted) if user.cpf_encrypted else ""
        if cpf:
            try:
                from ondeline_api.adapters.sgp.linknetam import (
                    SgpLinkNetAMProvider,
                )
                from ondeline_api.adapters.sgp.ondeline import (
                    SgpOndelineProvider,
                )
                from ondeline_api.adapters.sgp.router import SgpRouter
                from ondeline_api.config import get_settings
                from ondeline_api.services.sgp_cache import SgpCacheService
                from ondeline_api.services.sgp_config import load_sgp_config
                from ondeline_api.workers.runtime import get_redis

                s = get_settings()
                sgp_ond = await load_sgp_config(session, "ondeline")
                sgp_lnk = await load_sgp_config(session, "linknetam")
                router = SgpRouter(
                    primary=SgpOndelineProvider(**sgp_ond),
                    secondary=SgpLinkNetAMProvider(**sgp_lnk),
                )
                cache = SgpCacheService(
                    redis=await get_redis(),
                    session=session,
                    router=router,
                    ttl_cliente=s.sgp_cache_ttl_cliente,
                    ttl_negativo=s.sgp_cache_ttl_negativo,
                )
                await cache.invalidate(cpf)
                await router.aclose()
            except Exception:
                pass  # best-effort

    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        return FaturasOut(items=[])
    titulos = list(sgp.titulos)
    if status == "abertas":
        titulos = [t for t in titulos if t.status == "aberto"]
    elif status == "pagas":
        titulos = [t for t in titulos if t.status != "aberto"]

    # Ordenacao:
    # - abertas: ASC por vencimento (mais urgente primeiro)
    # - pagas e geral: DESC por vencimento (mais recente primeiro)
    is_abertas = status == "abertas"
    titulos.sort(key=lambda t: t.vencimento, reverse=not is_abertas)

    from datetime import datetime as _dt

    hoje = _dt.now(tz=UTC).date()
    return FaturasOut(items=[_fatura_out(t, hoje) for t in titulos])


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


class PushTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: str | None = Field(default=None, max_length=16)  # "android" | "ios"


@router.post("/me/push-token", status_code=204)
async def set_push_token(
    body: PushTokenIn,
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Registra/atualiza o token FCM do device. Idempotente."""
    if user.push_token == body.token:
        return  # ja registrado
    user.push_token = body.token
    await session.flush()
    await session.commit()


@router.delete("/me/push-token", status_code=204)
async def clear_push_token(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Limpa o token FCM (chamado no logout pra parar de receber push)."""
    if user.push_token is None:
        return
    user.push_token = None
    await session.flush()
    await session.commit()
