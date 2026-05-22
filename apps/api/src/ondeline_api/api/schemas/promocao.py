"""Schemas Pydantic de promoções."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PROMO_TIPOS = {"generica", "indicacao"}
PROMO_SEGMENTOS_FIXOS = {"todos", "inadimplentes", "adimplentes"}


def _valid_segmento(v: str) -> str:
    if v in PROMO_SEGMENTOS_FIXOS:
        return v
    if v.startswith("plano:") and len(v) > len("plano:"):
        return v
    raise ValueError(
        "segmento invalido (use 'todos', 'inadimplentes', 'adimplentes' ou 'plano:<id>')"
    )


class PromocaoBaseIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    subtitulo: str = Field(default="", max_length=240)
    imagem_url: str | None = None
    cta_label: str = Field(default="Saiba mais", max_length=40)
    cta_action: str = Field(default="info", max_length=240)
    tipo: str = Field(default="generica")
    ativa: bool = True
    ordem: int = 0
    valido_de: datetime | None = None
    valido_ate: datetime | None = None
    segmento: str = "todos"
    gradient_from: str | None = None
    gradient_to: str | None = None
    icon: str | None = None

    @field_validator("tipo")
    @classmethod
    def _check_tipo(cls, v: str) -> str:
        if v not in PROMO_TIPOS:
            raise ValueError(f"tipo invalido (use: {sorted(PROMO_TIPOS)})")
        return v

    @field_validator("segmento")
    @classmethod
    def _check_segmento(cls, v: str) -> str:
        return _valid_segmento(v)

    @field_validator("cta_action")
    @classmethod
    def _check_cta(cls, v: str) -> str:
        if v == "info" or v.startswith("url:") or v.startswith("tela:"):
            return v
        raise ValueError("cta_action deve ser 'info', 'url:<https>' ou 'tela:<rota>'")


class PromocaoCreateIn(PromocaoBaseIn):
    pass


class PromocaoUpdateIn(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=120)
    subtitulo: str | None = Field(default=None, max_length=240)
    imagem_url: str | None = None
    cta_label: str | None = Field(default=None, max_length=40)
    cta_action: str | None = None
    tipo: str | None = None
    ativa: bool | None = None
    ordem: int | None = None
    valido_de: datetime | None = None
    valido_ate: datetime | None = None
    segmento: str | None = None
    gradient_from: str | None = None
    gradient_to: str | None = None
    icon: str | None = None

    @field_validator("tipo")
    @classmethod
    def _check_tipo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in PROMO_TIPOS:
            raise ValueError(f"tipo invalido (use: {sorted(PROMO_TIPOS)})")
        return v

    @field_validator("segmento")
    @classmethod
    def _check_segmento(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _valid_segmento(v)

    @field_validator("cta_action")
    @classmethod
    def _check_cta(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v == "info" or v.startswith("url:") or v.startswith("tela:"):
            return v
        raise ValueError("cta_action deve ser 'info', 'url:<https>' ou 'tela:<rota>'")


class PromocaoOut(BaseModel):
    id: UUID
    titulo: str
    subtitulo: str
    imagem_url: str | None
    cta_label: str
    cta_action: str
    tipo: str
    ativa: bool
    ordem: int
    valido_de: datetime | None
    valido_ate: datetime | None
    segmento: str
    gradient_from: str | None
    gradient_to: str | None
    icon: str | None
    created_at: datetime
    updated_at: datetime


class PromocaoAdminOut(PromocaoOut):
    views: int = 0
    clicks: int = 0
    ctr: float = 0.0


class PromocaoEventoIn(BaseModel):
    tipo: str

    @field_validator("tipo")
    @classmethod
    def _check_tipo(cls, v: str) -> str:
        if v not in {"view", "click"}:
            raise ValueError("tipo deve ser 'view' ou 'click'")
        return v


class PromocaoEventoOut(BaseModel):
    ok: bool = True


class PromocaoReorderIn(BaseModel):
    ids: list[UUID]
