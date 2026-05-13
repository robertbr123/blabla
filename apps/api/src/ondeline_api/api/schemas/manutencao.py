"""DTOs for Manutencao."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ManutencaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    titulo: str
    descricao: str | None
    inicio_at: datetime
    fim_at: datetime
    cidades: list[str] | None
    notificar: bool
    criada_em: datetime


class ManutencaoCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=4000)
    inicio_at: datetime
    fim_at: datetime
    cidades: list[str] | None = None
    notificar: bool = True


class ManutencaoPatch(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=4000)
    inicio_at: datetime | None = None
    fim_at: datetime | None = None
    cidades: list[str] | None = None
    notificar: bool | None = None
