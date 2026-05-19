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


class ComissaoConfigOut(BaseModel):
    """Config de cálculo de comissão (lida da tabela `config`)."""

    valor_por_os: float
    bonus_csat_5: float
    bonus_csat_4: float


class ProdutividadeTecnicoOut(BaseModel):
    """F9 — Ranking + métricas de produtividade + comissão calculada."""

    tecnico_id: str
    nome: str
    os_concluidas: int
    os_csat_5: int  # OSes com CSAT = 5 (excelente)
    os_csat_4: int  # OSes com CSAT = 4 (bom)
    os_sem_csat: int
    csat_avg: float | None
    tempo_medio_min: int | None
    ultima_os_em: str | None
    comissao_base: float       # os_concluidas * valor_por_os
    comissao_bonus: float      # bonus_csat_5 + bonus_csat_4
    comissao_total: float


class ProdutividadeResponse(BaseModel):
    mes: str  # "YYYY-MM"
    config: ComissaoConfigOut
    tecnicos: list[ProdutividadeTecnicoOut]


class TimeseriesPontoOut(BaseModel):
    """Ponto diario da serie de metricas."""

    dia: str  # "YYYY-MM-DD"
    msgs: int
    os_concluidas: int
    leads_novos: int
    csat_avg: float | None


class TimeseriesOut(BaseModel):
    days: int
    pontos: list[TimeseriesPontoOut]
