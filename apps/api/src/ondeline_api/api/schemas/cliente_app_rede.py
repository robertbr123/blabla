"""Schemas para /api/v1/cliente-app/rede/* (app do cliente).

Diferente do schema do tecnico (api/schemas/rede.py): aqui o CPF NUNCA vem no
body — e derivado do token do cliente logado. Resposta enxuta (sem device_id/
internals do GenieACS).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RedeWifiOut(BaseModel):
    ssid: str


class RedeClienteStatusOut(BaseModel):
    # encontrada=False -> app mostra tela "em construcao" (cliente sem ONU no
    # GenieACS ainda).
    encontrada: bool
    online: bool = False
    modelo: str | None = None
    redes: list[RedeWifiOut] = Field(default_factory=list)


class TrocarSenhaClienteIn(BaseModel):
    # SEM cpf: o cliente so pode trocar a propria rede (CPF do token).
    senha: str = Field(min_length=8, max_length=63)
    contrato_id: str | None = None  # qual contrato (multi-contrato); None = atual


class AparelhoClienteOut(BaseModel):
    nome: str
    ip: str


class AparelhosClienteOut(BaseModel):
    encontrada: bool
    total: int = 0
    aparelhos: list[AparelhoClienteOut] = Field(default_factory=list)
    # "excelente" | "boa" | "fraca" | "indisponivel"
    saude: str = "indisponivel"


class TrocarSenhaClienteOut(BaseModel):
    status: str  # "enviado"
    reiniciando: bool
    aviso: str
