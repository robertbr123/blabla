"""DTOs de estoque (F6)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_CATEGORIAS = ("onu", "roteador", "cabo", "conector", "outro")
_TIPOS = (
    "entrada",
    "saida",
    "recolhido",
    "devolucao",
    "perda",
    "ajuste_positivo",
    "ajuste_negativo",
)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sku: str
    nome: str
    categoria: str
    serializado: bool
    ativo: bool
    created_at: datetime


class ItemCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    nome: str = Field(min_length=1, max_length=120)
    categoria: str = Field(pattern="^(onu|roteador|cabo|conector|outro)$")
    serializado: bool = False
    ativo: bool = True


class ItemUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    categoria: str | None = Field(
        default=None, pattern="^(onu|roteador|cabo|conector|outro)$"
    )
    ativo: bool | None = None


class MovimentoCreate(BaseModel):
    item_id: UUID
    tipo: str = Field(
        pattern="^(entrada|saida|recolhido|devolucao|perda|ajuste_positivo|ajuste_negativo)$"
    )
    quantidade: int = Field(gt=0)
    tecnico_id: UUID | None = None
    serial: str | None = Field(default=None, max_length=120)
    ordem_servico_id: UUID | None = None
    observacao: str | None = None


class MovimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    tecnico_id: UUID | None
    tipo: str
    quantidade: int
    serial: str | None
    ordem_servico_id: UUID | None
    observacao: str | None
    criado_por: UUID
    criado_em: datetime


class SaldoLinha(BaseModel):
    item_id: str
    sku: str
    nome: str
    categoria: str
    serializado: bool
    saldo: int


class SaldoOut(BaseModel):
    tecnico_id: UUID
    linhas: list[SaldoLinha]
