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
    relatorio: str | None = Field(default=None, max_length=5000)
    houve_visita: bool = True
    materiais: str | None = Field(default=None, max_length=2000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class FcmTokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    platform: str = Field(pattern=r"^(android|ios)$")


class FcmTokenRevokeIn(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class MudarSenhaIn(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=200)
    senha_nova: str = Field(min_length=8, max_length=200)


class PerfilEstatisticas(BaseModel):
    os_pendentes: int
    os_em_andamento: int
    os_concluidas_mes: int
    csat_avg_mes: float | None


class PerfilOut(BaseModel):
    user_id: str
    email: str
    nome: str
    whatsapp: str | None
    role: str
    foto_b64: str | None
    ativo: bool
    last_gps_ts: str | None
    estatisticas: PerfilEstatisticas
