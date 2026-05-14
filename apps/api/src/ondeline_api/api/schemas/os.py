"""DTOs for OrdemServico (OS)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OsListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    codigo: str
    cliente_id: UUID
    tecnico_id: UUID | None
    status: str
    problema: str
    endereco: str
    agendamento_at: datetime | None
    criada_em: datetime
    concluida_em: datetime | None
    reatribuido_em: datetime | None = None
    reatribuido_por: UUID | None = None


class OsOut(OsListItem):
    fotos: list[dict[str, Any]] | None
    csat: int | None
    comentario_cliente: str | None
    historico_reatribuicoes: list[dict[str, Any]] | None = None
    follow_up_resposta: str | None = None
    follow_up_respondido_em: datetime | None = None
    follow_up_resultado: str | None = None


class OsCreate(BaseModel):
    cliente_id: UUID
    tecnico_id: UUID
    problema: str = Field(min_length=1, max_length=2000)
    endereco: str = Field(min_length=1, max_length=500)
    agendamento_at: datetime | None = None


class OsPatch(BaseModel):
    status: str | None = None
    tecnico_id: UUID | None = None
    agendamento_at: datetime | None = None


class OsConcluirIn(BaseModel):
    csat: int | None = Field(default=None, ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=2000)


class OsReatribuirIn(BaseModel):
    tecnico_id: UUID


class OsDeleteOut(BaseModel):
    notif_tecnico: bool
