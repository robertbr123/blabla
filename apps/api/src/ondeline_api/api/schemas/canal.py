"""DTOs do canal (F4 + Cloud API)."""
from __future__ import annotations

from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CanalProvider = Literal["evolution", "cloud"]


class CanalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    nome: str
    provider: CanalProvider
    evolution_instance: str | None = None
    cloud_phone_id: str | None = None
    cloud_waba_id: str | None = None
    prompt_variant: str
    ativo: bool
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None
    created_at: datetime


class CanalCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    nome: str = Field(min_length=1, max_length=80)
    provider: CanalProvider = "evolution"
    # Evolution: obrigatorio se provider='evolution'.
    evolution_instance: str | None = Field(default=None, max_length=80)
    # Cloud API (Meta): obrigatorio se provider='cloud'.
    cloud_phone_id: str | None = Field(default=None, max_length=40)
    cloud_waba_id: str | None = Field(default=None, max_length=40)
    prompt_variant: str = Field(default="default", max_length=40)
    ativo: bool = True
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None

    @model_validator(mode="after")
    def _check_provider_fields(self) -> CanalCreate:
        if self.provider == "evolution":
            if not self.evolution_instance:
                raise ValueError("evolution_instance e obrigatorio quando provider='evolution'")
        elif self.provider == "cloud":
            if not self.cloud_phone_id:
                raise ValueError("cloud_phone_id e obrigatorio quando provider='cloud'")
        return self


class CanalUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=80)
    provider: CanalProvider | None = None
    evolution_instance: str | None = Field(default=None, max_length=80)
    cloud_phone_id: str | None = Field(default=None, max_length=40)
    cloud_waba_id: str | None = Field(default=None, max_length=40)
    prompt_variant: str | None = Field(default=None, max_length=40)
    ativo: bool | None = None
    horario_inicio: time | None = None
    horario_fim: time | None = None
    msg_fora_horario: str | None = None
