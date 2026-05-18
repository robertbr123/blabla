"""DTOs do canal (F4)."""
from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CanalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    nome: str
    evolution_instance: str
    prompt_variant: str
    ativo: bool
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None
    created_at: datetime


class CanalCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    nome: str = Field(min_length=1, max_length=80)
    evolution_instance: str = Field(min_length=1, max_length=80)
    prompt_variant: str = Field(default="default", max_length=40)
    ativo: bool = True
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None


class CanalUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=80)
    evolution_instance: str | None = Field(default=None, max_length=80)
    prompt_variant: str | None = Field(default=None, max_length=40)
    ativo: bool | None = None
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None
