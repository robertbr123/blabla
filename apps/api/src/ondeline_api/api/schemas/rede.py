"""Schemas para /api/v1/rede/*."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RedeWlanOut(BaseModel):
    instancia: int
    ssid: str
    enabled: bool


class StatusRedeOut(BaseModel):
    encontrada: bool
    device_id: str | None = None
    fabricante: str | None = None
    modelo: str | None = None
    online: bool = False
    last_inform: datetime | None = None
    redes: list[RedeWlanOut] = Field(default_factory=list)
    pppoe_login: str | None = None
    motivo: str | None = None  # quando encontrada=False


class StatusRedeIn(BaseModel):
    # CPF no body (nao no path) pra nao vazar em access log. O cliente e
    # localizado por CPF -> SGP -> pppoe -> ONU (cobre clientes antigos).
    cpf: str = Field(min_length=11, max_length=18)
    serial: str | None = None


class TrocarSenhaIn(BaseModel):
    cpf: str = Field(min_length=11, max_length=18)
    senha: str = Field(min_length=8, max_length=63)
    serial: str | None = None


class TrocarSenhaOut(BaseModel):
    status: str  # "enviado"
    device_id: str
    reiniciando: bool
    aviso: str


class AparelhoOut(BaseModel):
    nome: str
    ip: str
    mac: str
    ativo: bool
    interface: str = ""


class SinalFibraOut(BaseModel):
    rx_power: float | None = None
    tx_power: float | None = None
    status_gpon: str | None = None
    conexao_pppoe: str | None = None
    ip_externo: str | None = None
    uptime_s: int | None = None
    ultimo_erro: str | None = None


class DiagnosticoIn(BaseModel):
    cpf: str = Field(min_length=11, max_length=18)
    serial: str | None = None


class DiagnosticoOut(BaseModel):
    encontrada: bool
    last_inform: datetime | None = None
    aparelhos: list[AparelhoOut] = Field(default_factory=list)
    sinal: SinalFibraOut | None = None
    motivo: str | None = None  # quando encontrada=False
