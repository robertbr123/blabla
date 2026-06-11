"""Schemas dos endpoints de rede escopados por conversa (dashboard)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TrocarSenhaConversaIn(BaseModel):
    senha: str = Field(min_length=8, max_length=63)


class RebootOut(BaseModel):
    status: str  # "enviado"
    device_id: str
    aviso: str
