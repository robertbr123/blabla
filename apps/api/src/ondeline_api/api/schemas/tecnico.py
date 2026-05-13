"""DTOs for Tecnico + TecnicoArea."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TecnicoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nome: str
    whatsapp: str | None
    ativo: bool
    user_id: UUID | None
    gps_lat: float | None
    gps_lng: float | None
    gps_ts: datetime | None


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cidade: str
    rua: str
    prioridade: int


class TecnicoOut(TecnicoListItem):
    areas: list[AreaOut] = Field(default_factory=list)


class TecnicoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    whatsapp: str | None = Field(default=None, max_length=64)
    ativo: bool = True
    user_id: UUID | None = None


class TecnicoPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    whatsapp: str | None = Field(default=None, max_length=64)
    ativo: bool | None = None
    gps_lat: float | None = None
    gps_lng: float | None = None


class AreaCreate(BaseModel):
    cidade: str = Field(min_length=1, max_length=80)
    rua: str = Field(min_length=1, max_length=120)
    prioridade: int = Field(default=1, ge=1, le=10)
