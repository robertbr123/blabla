"""DTOs for Lead."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nome: str
    whatsapp: str
    interesse: str | None
    status: str
    atendente_id: UUID | None
    notas: str | None
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    whatsapp: str = Field(min_length=1, max_length=64)
    interesse: str | None = Field(default=None, max_length=255)
    atendente_id: UUID | None = None
    notas: str | None = Field(default=None, max_length=4000)


class LeadPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    interesse: str | None = Field(default=None, max_length=255)
    status: str | None = None
    atendente_id: UUID | None = None
    notas: str | None = Field(default=None, max_length=4000)
