"""DTOs de cliente_equipamento (F8)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClienteEquipamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cliente_id: UUID
    item_id: UUID
    item_sku: str
    item_nome: str
    item_categoria: str
    serial: str
    instalado_em_os_id: UUID | None = None
    instalado_em_os_codigo: str | None = None
    instalado_por_tecnico_id: UUID | None = None
    instalado_por_tecnico_nome: str | None = None
    instalado_em: datetime
    removido_em: datetime | None = None
    removido_em_os_id: UUID | None = None
    removido_em_os_codigo: str | None = None
