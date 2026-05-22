"""Endpoint de status da conexao do cliente.

MVP usa o status do contrato SGP (ativo/suspenso/cancelado) como proxy
de "servico operacional". Telemetria de PPPoE em tempo real (up/down,
sinal optico, uptime) entra quando o adapter SGP expuser.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/cliente-app/conexao", tags=["cliente-app:conexao"])


class ConexaoOut(BaseModel):
    # Status normalizado pro app:
    # 'ativo' (verde), 'suspenso' (amarelo), 'cancelado' (vermelho),
    # 'desconhecido' (cinza — sem contrato encontrado).
    status: str = Field(description="ativo | suspenso | cancelado | desconhecido")
    motivo: str = ""
    plano: str | None = None
    cidade: str | None = None
    # Indica se status veio de telemetria real (PPPoE up/down) ou apenas
    # do status do contrato no SGP. Hoje sempre False.
    tem_telemetria_real: bool = False


def _normalize_status(raw: str) -> str:
    """SGP retorna textos livres tipo 'Ativo', 'Suspenso por falta de pagamento'.

    Normaliza pros 3 estados que o app sabe renderizar.
    """
    s = raw.strip().lower()
    if not s:
        return "desconhecido"
    if "cancel" in s or "encerr" in s or "rescind" in s:
        return "cancelado"
    if "suspens" in s or "bloque" in s or "desativ" in s or "corte" in s:
        return "suspenso"
    if "ativ" in s or "habilit" in s or "online" in s or "ok" in s:
        return "ativo"
    # Por seguranca, status desconhecido nao virou verde
    return "desconhecido"


@router.get("", response_model=ConexaoOut)
async def get_conexao(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> ConexaoOut:
    # Reusa helper de SGP do me.
    from ondeline_api.api.v1.cliente_app_me import _sgp_cliente

    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente nao encontrado no SGP",
        )
    if not sgp.contratos:
        return ConexaoOut(
            status="desconhecido",
            motivo="Nenhum contrato vinculado.",
        )

    # Pega o primeiro contrato ativo, senao o primeiro qualquer.
    contrato = next(
        (c for c in sgp.contratos if _normalize_status(c.status) == "ativo"),
        sgp.contratos[0],
    )
    status_norm = _normalize_status(contrato.status)
    motivo = ""
    if status_norm != "ativo" and contrato.motivo_status:
        motivo = contrato.motivo_status
    elif status_norm == "suspenso":
        motivo = "Servico temporariamente suspenso."
    elif status_norm == "cancelado":
        motivo = "Contrato encerrado."
    return ConexaoOut(
        status=status_norm,
        motivo=motivo,
        plano=contrato.plano or None,
        cidade=contrato.cidade or None,
        tem_telemetria_real=False,
    )

