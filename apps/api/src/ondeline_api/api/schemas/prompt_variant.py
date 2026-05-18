"""DTOs de PromptVariant (F5)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PromptVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nome: str
    system_prompt: str
    ativo: bool
    trafego_pct: int
    canal_slug: str | None = None
    created_at: datetime
    created_by: UUID | None = None


class PromptVariantCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    system_prompt: str = Field(min_length=20)
    ativo: bool = True
    trafego_pct: int = Field(ge=0, le=100, default=0)
    canal_slug: str | None = None


class PromptVariantUpdate(BaseModel):
    system_prompt: str | None = Field(default=None, min_length=20)
    ativo: bool | None = None
    trafego_pct: int | None = Field(default=None, ge=0, le=100)
    canal_slug: str | None = None


class PromptVariantStats(BaseModel):
    """Distribuição atual de conversas por variante."""

    contagem: dict[str, int]
    total_trafego_ativo: int
