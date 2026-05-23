"""Streak de pagamento — engajamento.

Conta sequencia de faturas pagas mais recentes (sem atraso visivel).
Calculado on-the-fly a partir do cache SGP (sem tabela nova). Quando
ha fatura vencida e em aberto, streak quebra. Faturas em aberto mas
nao vencidas sao ignoradas (mes ainda nao fechou).
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.api.v1.cliente_app_me import _sgp_cliente
from ondeline_api.auth.cliente_deps import get_current_cliente_user
from ondeline_api.db.models.cliente_app import ClienteAppUser
from ondeline_api.deps import get_db

router = APIRouter(
    prefix="/api/v1/cliente-app",
    tags=["cliente-app:streak"],
)


class StreakOut(BaseModel):
    atual: int
    total_pagas: int


def _vencimento_to_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


@router.get("/streak", response_model=StreakOut)
async def get_streak(
    user: ClienteAppUser = Depends(get_current_cliente_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> StreakOut:
    sgp = await _sgp_cliente(session, user.cpf_encrypted)
    if sgp is None:
        return StreakOut(atual=0, total_pagas=0)

    hoje = datetime.now(tz=UTC).date()

    # Ordena por vencimento desc (mais recente primeiro).
    titulos = sorted(
        sgp.titulos,
        key=lambda t: t.vencimento,
        reverse=True,
    )

    streak = 0
    total_pagas = 0
    for t in titulos:
        if t.status == "pago":
            total_pagas += 1

    # Calcula streak: itera do mais recente pro mais antigo.
    for t in titulos:
        venc = _vencimento_to_date(t.vencimento)
        if t.status == "pago":
            streak += 1
            continue
        # Aberta nao vencida: ainda nao precisou pagar, nao quebra.
        if t.status == "aberto" and venc is not None and venc >= hoje:
            continue
        # Qualquer outra coisa (aberta vencida, cancelada, etc): para.
        break

    return StreakOut(atual=streak, total_pagas=total_pagas)
