"""Router admin pra metricas de OTP (Cloud vs Evolution).

Le os Counters Prometheus ``ondeline_otp_send_total{provider,result}`` e
agrega num formato amigavel pro dashboard. Os contadores sao cumulativos
desde o startup da API — depois de um restart, comecam do zero.

Fase 2.3 do plano de evolucao.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role, User
from ondeline_api.observability.metrics import otp_send_total

router = APIRouter(
    prefix="/api/v1/admin/otp-metricas",
    tags=["admin:otp-metricas"],
)


class OtpProviderStats(BaseModel):
    """Stats agregados de um provider."""
    success: int = 0
    fallback_to_evolution: int = 0
    error: int = 0

    @property
    def total(self) -> int:
        return self.success + self.fallback_to_evolution + self.error


class OtpMetricasOut(BaseModel):
    cloud: OtpProviderStats
    evolution: OtpProviderStats
    # Taxas em fracao 0.0-1.0 (frontend formata como %)
    cloud_success_rate: float
    cloud_fallback_rate: float
    # Total geral
    total: int


def _read_counters() -> dict[tuple[str, str], int]:
    """Le os samples do counter direto via ``otp_send_total.collect()``.

    Retorna {(provider, result): valor}. Mais robusto que iterar o REGISTRY:
    nao depende de comparar nome do metric familly (com/sem ``_total``).
    """
    out: dict[tuple[str, str], int] = {}
    for metric in otp_send_total.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            provider = sample.labels.get("provider", "")
            result = sample.labels.get("result", "")
            if provider and result:
                out[(provider, result)] = int(sample.value)
    return out


@router.get("", response_model=OtpMetricasOut)
async def get_otp_metricas(
    _user: User = Depends(require_role(Role.ADMIN)),  # noqa: B008
) -> OtpMetricasOut:
    """Devolve metricas de OTP agregadas por provider."""
    data = _read_counters()

    cloud = OtpProviderStats(
        success=data.get(("cloud", "success"), 0),
        fallback_to_evolution=data.get(("cloud", "fallback_to_evolution"), 0),
        error=data.get(("cloud", "error"), 0),
    )
    evolution = OtpProviderStats(
        success=data.get(("evolution", "success"), 0),
        fallback_to_evolution=data.get(("evolution", "fallback_to_evolution"), 0),
        error=data.get(("evolution", "error"), 0),
    )

    cloud_total = cloud.total
    cloud_success_rate = cloud.success / cloud_total if cloud_total > 0 else 0.0
    cloud_fallback_rate = (
        cloud.fallback_to_evolution / cloud_total if cloud_total > 0 else 0.0
    )

    return OtpMetricasOut(
        cloud=cloud,
        evolution=evolution,
        cloud_success_rate=cloud_success_rate,
        cloud_fallback_rate=cloud_fallback_rate,
        total=cloud_total + evolution.total,
    )
