"""GET /api/v1/conversas/{id}/rede/* - rede do cliente DENTRO da conversa.

O CPF e derivado do cliente VINCULADO a conversa (conversa.cliente_id -> Cliente
-> decrypt), nunca do body: o atendente so age no cliente daquela conversa.
Reusa o RedeService (Fatia 2) e os mappers de api/v1/rede.py. Liberado pra
ADMIN/ATENDENTE/TECNICO (os /api/v1/rede/* continuam TECNICO/ADMIN).
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.api.schemas.conversa_rede import RebootOut, TrocarSenhaConversaIn
from ondeline_api.api.schemas.rede import DiagnosticoOut, StatusRedeOut, TrocarSenhaOut
from ondeline_api.api.v1.rede import (
    AVISO_REBOOT,
    diagnostico_out,
    get_rede_service,
    status_out,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    CpfInvalidoError,
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas:rede"])
_role_dep = Depends(require_role(Role.ADMIN, Role.ATENDENTE, Role.TECNICO))


class ConversaSemClienteError(Exception):
    """Conversa nao tem cliente vinculado -> nao da pra resolver a ONU."""


async def _cpf_da_conversa(session: AsyncSession, conversa_id: UUID) -> str:
    conv = await session.get(Conversa, conversa_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversa nao encontrada")
    if conv.cliente_id is None:
        raise ConversaSemClienteError()
    cli = (
        await session.execute(select(Cliente).where(Cliente.id == conv.cliente_id))
    ).scalar_one_or_none()
    if cli is None or not cli.cpf_cnpj_encrypted:
        raise ConversaSemClienteError()
    return decrypt_pii(cli.cpf_cnpj_encrypted)


def _sem_cliente_http() -> HTTPException:
    return HTTPException(status_code=409, detail="conversa sem cliente vinculado")


@router.get(
    "/{conversa_id}/rede/status", response_model=StatusRedeOut, dependencies=[_role_dep]
)
async def status_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> StatusRedeOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        st = await service.status_rede(cpf)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return status_out(st)


@router.get(
    "/{conversa_id}/rede/diagnostico",
    response_model=DiagnosticoOut,
    dependencies=[_role_dep],
)
async def diagnostico_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
) -> DiagnosticoOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        diag = await service.diagnostico_rede(cpf)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return diagnostico_out(diag)


@router.post(
    "/{conversa_id}/rede/wifi/senha",
    response_model=TrocarSenhaOut,
    dependencies=[_role_dep],
)
async def trocar_senha_conversa(
    conversa_id: UUID,
    payload: TrocarSenhaConversaIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> TrocarSenhaOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        res = await service.trocar_senha_wifi(
            cpf=cpf, nova_senha=payload.senha, serial=None, ator_user_id=user.id
        )
    except (SenhaInvalidaError, CpfInvalidoError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaOut(
        status="enviado", device_id=res.device_id, reiniciando=res.reiniciando, aviso=aviso
    )


@router.post(
    "/{conversa_id}/rede/reboot", response_model=RebootOut, dependencies=[_role_dep]
)
async def reboot_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> RebootOut:
    try:
        cpf = await _cpf_da_conversa(session, conversa_id)
    except ConversaSemClienteError as e:
        raise _sem_cliente_http() from e
    try:
        res = await service.reiniciar_onu(cpf=cpf, serial=None, ator_user_id=user.id)
    except CpfInvalidoError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    return RebootOut(status="enviado", device_id=res.device_id, aviso=AVISO_REBOOT)
