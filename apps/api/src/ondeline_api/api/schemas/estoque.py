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


class DepositoSaldoOut(BaseModel):
    """Saldo do deposito central (tecnico_id IS NULL)."""
    linhas: list[SaldoLinha]


class DepositoEntradaIn(BaseModel):
    """Lancamento de entrada no deposito (compra, recebimento de fornecedor)."""
    item_id: UUID
    quantidade: int = Field(gt=0)
    serial: str | None = Field(default=None, max_length=120)
    observacao: str | None = Field(default=None, max_length=500)


class DepositoBaixaIn(BaseModel):
    """Baixa direta do deposito (perda, ajuste). Nao vai pra tecnico."""
    item_id: UUID
    quantidade: int = Field(gt=0)
    tipo: str = Field(pattern="^(perda|ajuste_negativo)$")
    serial: str | None = Field(default=None, max_length=120)
    observacao: str | None = Field(default=None, max_length=500)


class TransferirIn(BaseModel):
    """Transferencia deposito -> tecnico (atomica: saida + entrada)."""
    item_id: UUID
    tecnico_id: UUID
    quantidade: int = Field(gt=0)
    serial: str | None = Field(default=None, max_length=120)
    observacao: str | None = Field(default=None, max_length=500)


class TecnicoSaldoResumo(BaseModel):
    """Linha da visao admin: saldo por tecnico x item."""
    tecnico_id: UUID
    tecnico_nome: str
    item_id: UUID
    sku: str
    nome: str
    categoria: str
    saldo: int


class TecnicoSaldoOut(BaseModel):
    """Saldo de todos os tecnicos x itens (admin visualiza distribuicao)."""
    linhas: list[TecnicoSaldoResumo]
