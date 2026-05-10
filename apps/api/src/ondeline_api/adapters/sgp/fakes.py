"""Fakes SGP scriptaveis."""
from __future__ import annotations

from ondeline_api.adapters.sgp.base import ClienteSgp, Fatura, SgpProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


class FakeSgpProvider(SgpProvider):
    name = SgpProviderEnum.ONDELINE

    def __init__(
        self,
        *,
        clientes: dict[str, ClienteSgp] | None = None,
        faturas: dict[str, list[Fatura]] | None = None,
        raise_on: set[str] | None = None,
    ) -> None:
        self._clientes = clientes or {}
        self._faturas = faturas or {}
        self._raise_on = raise_on or set()

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        if cpf in self._raise_on:
            raise RuntimeError("SGP forced failure")
        return self._clientes.get(cpf)

    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]:
        fts = self._faturas.get(sgp_id, [])
        if apenas_abertas:
            return [f for f in fts if f.status == "aberto"]
        return list(fts)

    async def aclose(self) -> None:
        return None
