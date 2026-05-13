"""DTOs for /api/v1/tecnico/me/*."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GpsUpdate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class IniciarIn(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class ConcluirIn(BaseModel):
    csat: int | None = Field(default=None, ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=2000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
