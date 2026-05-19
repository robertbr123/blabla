"""DTOs pra clientes cadastrados em campo."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Input ────────────────────────────────────────────────────


class ClienteCampoIn(BaseModel):
    """Body do POST /clientes-campo. Plain text — backend encripta PII."""

    cpf: str = Field(min_length=11, max_length=14)
    nome: str = Field(min_length=1, max_length=255)
    dob: date
    telefone: str = Field(min_length=10, max_length=15)
    # Endereco
    cep: str | None = Field(default=None, max_length=10)
    address: str = Field(min_length=1, max_length=255)
    number: str = Field(min_length=1, max_length=10)
    complement: str | None = Field(default=None, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    # Plano
    plan_id: int | None = None
    plan_nome: str = Field(min_length=1, max_length=255)
    pppoe_user: str | None = Field(default=None, max_length=100)
    pppoe_pass: str | None = Field(default=None, max_length=100)
    due_date: int = Field(ge=1, le=28)
    # Equipamento + contrato + obs
    serial: str | None = Field(default=None, max_length=100)
    contrato: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    # Geo
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)


class ClienteCampoPatch(BaseModel):
    """PATCH parcial. Campos nao listados aqui sao imutaveis (cpf, dob, installer)."""

    nome: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=15)
    cep: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=255)
    number: str | None = Field(default=None, max_length=10)
    complement: str | None = Field(default=None, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    plan_id: int | None = None
    plan_nome: str | None = Field(default=None, max_length=255)
    pppoe_user: str | None = Field(default=None, max_length=100)
    pppoe_pass: str | None = Field(default=None, max_length=100)
    due_date: int | None = Field(default=None, ge=1, le=28)
    serial: str | None = Field(default=None, max_length=100)
    contrato: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)


class SyncSgpIn(BaseModel):
    sgp_id: str = Field(min_length=1, max_length=40)


# ── Output ──────────────────────────────────────────────────


class ClienteCampoListItem(BaseModel):
    """Versao reduzida pra listagem (sem PII descriptografada do telefone/pppoe).

    Nome e CPF descriptografados sao incluidos pra usuarios autenticados —
    e o que o tecnico precisa pra identificar o cliente.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cpf: str  # plain (descriptografado)
    nome: str
    address: str
    number: str
    neighborhood: str | None
    city: str
    plan_nome: str
    installer_nome: str
    sgp_synced_at: datetime | None
    sgp_id: str | None
    created_at: datetime


class ClienteCampoOut(BaseModel):
    """Detalhe completo. Todos os campos PII descriptografados."""

    id: UUID
    cpf: str
    nome: str
    dob: date
    telefone: str
    cep: str | None
    address: str
    number: str
    complement: str | None
    neighborhood: str | None
    city: str
    state: str | None
    plan_id: int | None
    plan_nome: str
    pppoe_user: str | None
    pppoe_pass: str | None
    due_date: int
    installer_user_id: UUID | None
    installer_nome: str
    serial: str | None
    contrato: str | None
    observation: str | None
    latitude: float | None
    longitude: float | None
    location_accuracy: float | None
    fotos: list[dict[str, Any]] | None
    registration_date: date
    sgp_synced_at: datetime | None
    sgp_id: str | None
    created_at: datetime
    updated_at: datetime


# ── SGP Planos ──────────────────────────────────────────────


class SgpPlano(BaseModel):
    id: int
    grupo: str | None = None
    descricao: str
    preco: float
    download: int      # Kbps
    upload: int        # Kbps
    qtd_servicos: int | None = None


class SgpPlanosOut(BaseModel):
    provider: str
    planos: list[SgpPlano]
