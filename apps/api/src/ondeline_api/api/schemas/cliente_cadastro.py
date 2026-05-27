"""DTOs pra clientes cadastrados em campo."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_due_date(value: int) -> int:
    if value not in (10, 20, 30):
        raise ValueError("due_date deve ser 10, 20 ou 30")
    return value

# ── Input ────────────────────────────────────────────────────


class MaterialUsado(BaseModel):
    """Item do estoque do tecnico consumido na instalacao."""

    item_id: UUID
    quantidade: int = Field(gt=0)
    serial: str | None = Field(default=None, max_length=120)


class ClienteCampoIn(BaseModel):
    """Body do POST /clientes-campo. Plain text — backend encripta PII."""

    cpf: str = Field(min_length=11, max_length=14)
    nome: str = Field(min_length=1, max_length=255)
    dob: date
    telefone: str = Field(min_length=10, max_length=15)
    email: str | None = Field(default=None, max_length=255)
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
    due_date: int = Field(ge=10, le=30)
    # Equipamento + contrato + obs
    serial: str | None = Field(default=None, max_length=100)
    contrato: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    # Geo
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)
    # Materiais consumidos na instalacao (opcional — pode ficar vazio)
    materiais: list[MaterialUsado] = Field(default_factory=list)

    _due_date_validator = field_validator("due_date")(_validate_due_date)


class ClienteCampoPatch(BaseModel):
    """PATCH parcial. Campos nao listados aqui sao imutaveis (cpf, dob, installer)."""

    nome: str | None = Field(default=None, max_length=255)
    telefone: str | None = Field(default=None, max_length=15)
    email: str | None = Field(default=None, max_length=255)
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
    due_date: int | None = Field(default=None, ge=10, le=30)
    serial: str | None = Field(default=None, max_length=100)
    contrato: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)

    _due_date_validator = field_validator("due_date")(_validate_due_date)


class SyncSgpIn(BaseModel):
    sgp_id: str = Field(min_length=1, max_length=40)


class ImportClienteRow(BaseModel):
    """Linha de import — formato compativel com o site MySQL antigo.

    `installer` aqui e texto livre (nome do tecnico no MySQL). Backend
    tenta match com `users.name` na importacao; se nao bater, deixa so o
    texto cacheado em installer_nome (installer_user_id fica NULL).
    """

    cpf: str = Field(min_length=11, max_length=14)
    name: str = Field(min_length=1, max_length=255)
    dob: date
    phone: str = Field(min_length=10, max_length=15)
    cep: str | None = Field(default=None, max_length=10)
    address: str = Field(min_length=1, max_length=255)
    number: str = Field(min_length=1, max_length=10)
    complement: str | None = Field(default=None, max_length=255)
    neighborhood: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    plan: str = Field(min_length=1, max_length=255)
    plan_id: int | None = None
    pppoe_user: str | None = Field(default=None, max_length=100)
    pppoe_pass: str | None = Field(default=None, max_length=100)
    due_date: int = Field(ge=10, le=30)
    installer: str = Field(min_length=1, max_length=255)
    serial: str | None = Field(default=None, max_length=100)
    contrato: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_accuracy: float | None = Field(default=None, ge=0)
    registration_date: date

    _due_date_validator = field_validator("due_date")(_validate_due_date)


class ImportResult(BaseModel):
    """Resumo da importacao em batch."""

    inserted: int
    updated: int
    skipped: int
    errors: list[str]


class ImportBatchIn(BaseModel):
    """Body do POST /clientes-campo/import (JSON com lista)."""

    rows: list[ImportClienteRow]
    dry_run: bool = False
    mark_as_synced: bool = True  # vindo do MySQL, ja estao no SGP


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
    email: str | None
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


# ── Materiais usados ────────────────────────────────────────


class MaterialUsadoOut(BaseModel):
    """Item consumido na instalacao (vista de um cliente_cadastro)."""

    movimento_id: UUID
    item_id: UUID
    sku: str
    nome: str
    categoria: str
    unidade: str = "UN"
    serializado: bool
    quantidade: int
    serial: str | None
    criado_em: datetime
    criado_por: UUID
    observacao: str | None
