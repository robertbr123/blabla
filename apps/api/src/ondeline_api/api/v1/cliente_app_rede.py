"""GET/POST /api/v1/cliente-app/rede/* - cliente troca a propria senha WiFi.

Reusa RedeService + get_rede_service (a dependency NAO forca role; o role do
tecnico fica nas rotas de /api/v1/rede). O CPF vem do token (decrypt_pii), nunca
do body: o cliente so mexe na propria ONU. Cooldown anti-flood de reboots.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError, SinalFibra
from ondeline_api.api.schemas.cliente_app_rede import (
    AparelhoClienteOut,
    AparelhosClienteOut,
    RedeClienteStatusOut,
    RedeWifiOut,
    TrocarSenhaClienteIn,
    TrocarSenhaClienteOut,
)
from ondeline_api.api.v1.rede import get_rede_service
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.deps import get_db
from ondeline_api.services.rede_service import (
    CpfInvalidoError,
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)

router = APIRouter(prefix="/api/v1/cliente-app/rede", tags=["cliente-app:rede"])

COOLDOWN_MINUTOS = 5
AVISO_REBOOT = "Sua internet vai reiniciar e voltar em cerca de 2 minutos."


def _saude_from_sinal(sinal: SinalFibra | None) -> str:
    """Traduz o RX optico (dBm) num selo amigavel, escondendo o numero."""
    if sinal is None or sinal.rx_power is None:
        return "indisponivel"
    rx = sinal.rx_power
    if -24 <= rx <= -8:
        return "excelente"
    if -27 <= rx < -24:
        return "boa"
    return "fraca"  # rx < -27 (fraco) ou rx > -8 (forte demais)


def _so_digitos(cpf: str) -> str:
    return "".join(ch for ch in (cpf or "") if ch.isdigit())


async def _minutos_cooldown_restante(session: AsyncSession, cpf_digits: str) -> int:
    """Minutos que faltam pro cliente poder trocar de novo (0 = liberado).

    Olha a troca mais recente do mesmo cpf_hash dentro da janela. cpf_hash e
    escrito pelo RedeService como hash_pii(_so_digitos(cpf)); replicamos igual.
    """
    since = datetime.now(UTC) - timedelta(minutes=COOLDOWN_MINUTOS)
    stmt = select(func.max(RedeWifiPedido.created_at)).where(
        RedeWifiPedido.cpf_hash == hash_pii(cpf_digits),
        RedeWifiPedido.created_at >= since,
    )
    last = (await session.execute(stmt)).scalar_one_or_none()
    if last is None:
        return 0
    libera = last + timedelta(minutes=COOLDOWN_MINUTOS)
    restante = (libera - datetime.now(UTC)).total_seconds()
    return max(0, math.ceil(restante / 60))


@router.get("/status", response_model=RedeClienteStatusOut)
async def status_rede_cliente(
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    contrato_id: str | None = None,
) -> RedeClienteStatusOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    try:
        st = await service.status_rede(cpf, contrato_id=contrato_id)
    except CpfInvalidoError:
        # Cliente logado deveria ter CPF valido; trata defensivamente como
        # "sem ONU" (mostra em construcao) em vez de 500.
        return RedeClienteStatusOut(encontrada=False)
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not st.encontrada or st.device is None:
        return RedeClienteStatusOut(encontrada=False)
    d = st.device
    # SSIDs distintos, preservando ordem (uma ONU repete o SSID em 2.4 e 5G).
    vistos: list[str] = []
    for r in d.redes:
        if r.ssid and r.ssid not in vistos:
            vistos.append(r.ssid)
    return RedeClienteStatusOut(
        encontrada=True,
        online=d.online,
        modelo=d.modelo,
        redes=[RedeWifiOut(ssid=s) for s in vistos],
    )


@router.get("/aparelhos", response_model=AparelhosClienteOut)
async def aparelhos_rede_cliente(
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    contrato_id: str | None = None,
) -> AparelhosClienteOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    try:
        diag = await service.diagnostico_rede(cpf, contrato_id=contrato_id)
    except CpfInvalidoError:
        return AparelhosClienteOut(encontrada=False)
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e
    if not diag.encontrada or diag.device is None:
        return AparelhosClienteOut(encontrada=False)
    d = diag.device
    return AparelhosClienteOut(
        encontrada=True,
        total=len(d.aparelhos),
        aparelhos=[AparelhoClienteOut(nome=a.nome, ip=a.ip) for a in d.aparelhos],
        saude=_saude_from_sinal(d.sinal),
    )


@router.post("/wifi/senha", response_model=TrocarSenhaClienteOut)
async def trocar_senha_cliente(
    payload: TrocarSenhaClienteIn,
    user: Annotated[ClienteAppUser, Depends(get_current_cliente_user)],
    service: Annotated[RedeService, Depends(get_rede_service)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrocarSenhaClienteOut:
    cpf = decrypt_pii(user.cpf_encrypted)
    cpf_digits = _so_digitos(cpf)

    restante = await _minutos_cooldown_restante(session, cpf_digits)
    if restante > 0:
        raise HTTPException(
            status_code=429,
            detail={"erro": "cooldown", "minutos_restantes": restante},
        )

    try:
        res = await service.trocar_senha_wifi(
            cpf=cpf,
            nova_senha=payload.senha,
            serial=None,
            ator_user_id=user.id,
            contrato_id=payload.contrato_id,
        )
    except (SenhaInvalidaError, CpfInvalidoError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OnuNaoEncontradaError as e:
        raise HTTPException(status_code=404, detail="ONU nao encontrada") from e
    except GenieAcsUnavailableError as e:
        raise HTTPException(status_code=503, detail="GenieACS indisponivel") from e

    aviso = AVISO_REBOOT if res.reiniciando else "Senha enviada."
    return TrocarSenhaClienteOut(
        status="enviado", reiniciando=res.reiniciando, aviso=aviso
    )
