"""Tool: consulta a rede do cliente (aparelhos conectados + sinal da fibra).

Usada pelo bot quando o cliente reclama de internet lenta/instavel. Reusa o
RedeService (Fatia 2). Best-effort: GenieACS fora -> retorno amigavel, nunca
quebra o loop do LLM.
"""
from __future__ import annotations

from typing import Any, Protocol

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.services.rede_service import (
    DiagnosticoRede,
    RedeService,
    qualidade_sinal,
)
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}


class _RedeProto(Protocol):
    async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede: ...


async def _payload_consulta(rede: _RedeProto, cpf: str) -> dict[str, Any]:
    diag = await rede.diagnostico_rede(cpf)
    if not diag.encontrada or diag.device is None:
        return {"encontrada": False, "motivo": diag.motivo}
    d = diag.device
    rx = d.sinal.rx_power if d.sinal else None
    label, emoji = qualidade_sinal(rx)
    return {
        "encontrada": True,
        "online": d.online,
        "aparelhos_conectados": len(d.aparelhos),
        "sinal": {"rx_power": rx, "qualidade": label, "emoji": emoji},
    }


@tool(
    name="consultar_rede",
    description=(
        "Consulta a rede do cliente vinculado a esta conversa: quantos aparelhos "
        "estao conectados agora e a qualidade do sinal da fibra. Use quando o "
        "cliente reclamar de internet lenta, caindo ou instavel."
    ),
    parameters=SCHEMA,
)
async def consultar_rede(ctx: ToolContext) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"encontrada": False, "motivo": "cliente_nao_identificado"}
    cpf = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
    genie = GenieAcsClient(base_url=get_settings().genieacs_url)
    rede = RedeService(session=ctx.session, genieacs=genie, sgp_cache=ctx.sgp_cache)
    try:
        return await _payload_consulta(rede, cpf)
    except GenieAcsUnavailableError:
        return {"erro": "indisponivel"}
    finally:
        await genie.aclose()
