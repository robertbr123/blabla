"""DTOs for Tecnico + TecnicoArea."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class TecnicoUserOut(BaseModel):
    """Login info for the User linked to a Tecnico (PWA access)."""
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    email: str
    is_active: bool
    last_login_at: datetime | None


class TecnicoOut(TecnicoListItem):
    areas: list[AreaOut] = Field(default_factory=list)
    user: TecnicoUserOut | None = None


class TecnicoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    whatsapp: str | None = Field(default=None, max_length=64)
    ativo: bool = True
    user_id: UUID | None = None
    # Optional: create login user atomically. If `email` is given, `password` must be too.
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class TecnicoUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TecnicoUserResetPassword(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class TecnicoUserPatch(BaseModel):
    is_active: bool | None = None


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
