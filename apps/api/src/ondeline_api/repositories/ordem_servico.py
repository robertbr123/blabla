"""OrdemServicoRepo — create."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import OrdemServico, OsStatus


class OrdemServicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        codigo: str,
        cliente_id: UUID,
        tecnico_id: UUID | None,
        problema: str,
        endereco: str,
    ) -> OrdemServico:
        os_ = OrdemServico(
            codigo=codigo,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            problema=problema,
            endereco=endereco,
            status=OsStatus.PENDENTE,
        )
        self._session.add(os_)
        await self._session.flush()
        return os_
