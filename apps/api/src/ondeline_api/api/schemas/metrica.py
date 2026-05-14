"""DTOs for dashboard metrics."""
from __future__ import annotations

from pydantic import BaseModel


class MetricasOut(BaseModel):
    conversas_aguardando: int
    conversas_humano: int
    msgs_24h: int
    os_abertas: int
    os_concluidas_24h: int
    csat_avg_30d: float | None
    leads_novos_7d: int


class RankingTecnicoOut(BaseModel):
    tecnico_id: str
    nome: str
    os_concluidas: int
    csat_avg: float | None
    tempo_medio_min: int | None
    ultima_os_em: str | None
