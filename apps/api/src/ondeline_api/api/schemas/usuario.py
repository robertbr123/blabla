"""Schemas de /api/v1/usuarios — gestao de usuarios do dashboard (admin/atendente)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RoleDashboard = Literal["admin", "atendente"]


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: RoleDashboard
    is_active: bool
    cidades: list[str] = []
    last_login_at: datetime | None = None
    created_at: datetime


class UsuarioCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=120)
    role: RoleDashboard
    password: str = Field(min_length=8, max_length=128)
    cidades: list[str] = []


class UsuarioPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: RoleDashboard | None = None
    is_active: bool | None = None
    cidades: list[str] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
