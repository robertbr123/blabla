"""Tool: abre OS, roteia tecnico, notifica via WhatsApp."""
from __future__ import annotations

from typing import Any

from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problema": {
            "type": "string",
            "description": "Descricao curta do problema reportado",
        },
        "endereco": {
            "type": "string",
            "description": "Endereco completo (rua, numero, bairro, cidade)",
        },
    },
    "required": ["problema", "endereco"],
}


def _split_endereco(endereco: str) -> tuple[str, str]:
    """Tentativa best-effort de extrair (rua, cidade) do texto livre."""
    parts = [p.strip() for p in (endereco or "").split(",") if p.strip()]
    rua = parts[0] if parts else ""
    cidade = parts[-2] if len(parts) >= 2 else (parts[-1] if parts else "")
    return rua, cidade


@tool(
    name="abrir_ordem_servico",
    description=(
        "Cria uma Ordem de Servico (OS) tecnica para o cliente vinculado a esta conversa "
        "e roteia para o tecnico mais adequado por cidade/rua. Use quando o problema "
        "tecnico nao puder ser resolvido por orientacao."
    ),
    parameters=SCHEMA,
)
async def abrir_ordem_servico(
    ctx: ToolContext, *, problema: str, endereco: str
) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado"}

    codigo = await next_codigo(ctx.session)
    rua, cidade = _split_endereco(endereco)
    tecnico = await TecnicoRepo(ctx.session).find_by_area(cidade=cidade, rua=rua)
    os_ = await OrdemServicoRepo(ctx.session).create(
        codigo=codigo,
        cliente_id=ctx.cliente.id,
        tecnico_id=tecnico.id if tecnico else None,
        problema=problema,
        endereco=endereco,
    )

    if tecnico is not None and tecnico.whatsapp:
        nome_cliente = decrypt_pii(ctx.cliente.nome_encrypted) if ctx.cliente.nome_encrypted else "Cliente"
        msg = (
            f"Nova OS {codigo}\n"
            f"Cliente: {nome_cliente}\n"
            f"Endereco: {endereco}\n"
            f"Problema: {problema}"
        )
        await ctx.evolution.send_text(tecnico.whatsapp, msg)

    return {
        "ok": True,
        "codigo": codigo,
        "tecnico_nome": tecnico.nome if tecnico else None,
        "os_id": str(os_.id),
    }
