"""DTOs para planos de internet."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    preco: float = Field(gt=0)
    velocidade: str = Field(min_length=1, max_length=20)
    extras: list[str] = []
    descricao: str = ""
    ativo: bool = True
    destaque: bool = False


class PlanoOut(PlanoIn):
    index: int
