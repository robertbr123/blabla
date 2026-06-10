"""Interface GenieACS (TR-069). DTOs e excecao tecnica.

O GenieACS expoe os dados da ONU numa arvore aninhada (cada folha vira
um objeto com `_value`/`_writable`). Aqui isolamos isso em DTOs simples
que o service e o endpoint consomem sem conhecer o shape cru do NBI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "GenieAcsDevice",
    "GenieAcsUnavailableError",
    "RedeWlan",
]


class GenieAcsUnavailableError(RuntimeError):
    """Falha tecnica ao falar com o NBI do GenieACS (rede / HTTP != 2xx).

    Distinto de "device nao encontrado" (retorno None). O endpoint traduz
    isto em 503; nunca em "ONU nao encontrada".
    """


@dataclass(frozen=True, slots=True)
class RedeWlan:
    """Uma instancia WLANConfiguration da ONU (uma rede WiFi)."""

    instancia: int
    ssid: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class GenieAcsDevice:
    device_id: str
    fabricante: str = ""
    modelo: str = ""  # ProductClass (ex: "AX1800")
    serial: str = ""
    last_inform: datetime | None = None
    online: bool = False
    redes: list[RedeWlan] = field(default_factory=list)
