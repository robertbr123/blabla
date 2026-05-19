"""DTOs de Indicação (F10)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IndicacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    codigo: str
    cliente_indicador_id: UUID
    cliente_indicador_nome: str | None = None
    criado_em: datetime
    expira_em: datetime | None = None
    usos: int
    ativo: bool


class IndicacaoUsoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    indicacao_id: UUID
    indicacao_codigo: str | None = None
    lead_id: UUID | None = None
    lead_nome: str | None = None
    cliente_indicado_id: UUID | None = None
    cliente_indicado_nome: str | None = None
    criado_em: datetime
    convertido_em: datetime | None = None
    credito_aplicado_em: datetime | None = None
    observacao: str | None = None


class IndicacaoUsoMarcarConvertidoIn(BaseModel):
    cliente_indicado_id: UUID | None = None
    observacao: str | None = None


class IndicacaoUsoMarcarCreditoIn(BaseModel):
    observacao: str | None = None


class RankingIndicadorOut(BaseModel):
    cliente_id: UUID
    cliente_nome: str
    usos: int
    convertidos: int
