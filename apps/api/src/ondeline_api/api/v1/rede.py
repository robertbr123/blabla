"""GET/POST /api/v1/rede/{cadastro_id} - gerencia da rede WiFi via TR-069.

cadastro_id = UUID do ClienteCadastro (cliente cadastrado em campo). O app
tecnico navega com esse id. O service resolve a ONU pelo PPPoE do cadastro
(principal) com fallback no serial.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.api.schemas.rede import (
    RedeWlanOut,
    StatusRedeOut,
    TrocarSenhaIn,
    TrocarSenhaOut,
)
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.config import get_settings
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.sgp_config import load_sgp_config
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/rede", tags=["rede"])

_role_dep = Depends(require_role(Role.TECNICO, Role.ADMIN))

AVISO_REBOOT = "A internet do cliente vai reiniciar e voltar em cerca de 2 minutos."


async def get_rede_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncIterator[RedeService]:
    """Monta GenieAcsClient + SgpCacheService e injeta o RedeService.

    O SGP e a fonte do PPPoE. Sobrescrita inteira nos testes
    (app.dependency_overrides[get_rede_service]).
    """
    s = get_settings()
    redis = await get_redis()
    genie = GenieAcsClient(base_url=s.genieacs_url)
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
    try:
        yield RedeService(session=session, genieacs=genie, sgp_cache=cache)
    finally:
        await genie.aclose()
        await router_sgp.aclose()


@router.get("/{cadastro_id}", response_model=StatusRedeOut, dependencies=[_role_dep])
async def status_rede(
    cadastro_id: UUID,
    service: Annotated[RedeService, Depends(get_rede_service)],
    serial: str | None = None,
) -> StatusRedeOut:
    try:
        st = await service.status_rede(cadastro_id, serial)
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not st.encontrada or st.device is None:
        return StatusRedeOut(
            encontrada=False, pppoe_login=st.pppoe_login, motivo=st.motivo
        )
    d = st.device
    return StatusRedeOut(
        encontrada=True,
        device_id=d.device_id,
        fabricante=d.fabricante,
        modelo=d.modelo,
        online=d.online,
        last_inform=d.last_inform,
        redes=[RedeWlanOut(instancia=r.instancia, ssid=r.ssid, enabled=r.enabled) for r in d.redes],
        pppoe_login=st.pppoe_login,
    )


@router.post(
    "/{cadastro_id}/wifi/senha", response_model=TrocarSenhaOut, dependencies=[_role_dep]
)
async def trocar_senha(
    cadastro_id: UUID,
    payload: TrocarSenhaIn,
    service: Annotated[RedeService, Depends(get_rede_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> TrocarSenhaOut:
    try:
        res = await service.trocar_senha_wifi(
            cadastro_id=cadastro_id,
            nova_senha=payload.senha,
            serial=payload.serial,
            ator_user_id=user.id,
        )
    except SenhaInvalidaError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaOut(
        status="enviado",
        device_id=res.device_id,
        reiniciando=res.reiniciando,
        aviso=aviso,
    )
