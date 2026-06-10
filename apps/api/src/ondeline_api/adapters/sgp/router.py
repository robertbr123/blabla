"""SgpRouter — fan-out sequencial: tenta primario, fallback secundario.

Erros do primario nao sao fatais; logamos e seguimos. Reordenacao por
configuracao no construtor (e o caller que decide quem e Ondeline e quem e
LinkNetAM).
"""
from __future__ import annotations

import re

import structlog

from ondeline_api.adapters.sgp.base import ClienteSgp, SgpProvider, SgpUnavailableError

log = structlog.get_logger(__name__)

_DIGITS_RE = re.compile(r"\D+")


def _clean_cpf(cpf: str) -> str:
    return _DIGITS_RE.sub("", cpf or "")


class SgpRouter:
    def __init__(self, *, primary: SgpProvider, secondary: SgpProvider) -> None:
        self._primary = primary
        self._secondary = secondary

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        clean = _clean_cpf(cpf)
        unavailable = False
        for prov in (self._primary, self._secondary):
            try:
                cli = await prov.buscar_por_cpf(clean)
            except Exception as e:
                log.warning(
                    "sgp.router.provider_error",
                    provider=prov.name.value,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                unavailable = True
                continue
            if cli is not None:
                return cli
        if unavailable:
            # Pelo menos um provider falhou tecnicamente e ninguem achou o
            # cliente - "nao encontrado" nao e confiavel. O caller (cache)
            # serve stale ou propaga; nunca cacheia negativo.
            raise SgpUnavailableError("nenhum provider SGP respondeu com sucesso")
        return None

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._secondary.aclose()
