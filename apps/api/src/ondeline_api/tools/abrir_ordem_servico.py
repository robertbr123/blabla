"""Tool: abre OS, roteia tecnico por cidade/rua do cadastro SGP, notifica via WhatsApp.

O LLM NAO precisa (e nao deve) inventar endereco — a tool resolve a partir do
cliente vinculado a conversa, lendo o cadastro fresco no SGP. O parametro
`endereco` so deve ser passado quando o cliente *especificar* um endereco
diferente do cadastro (ex: 'a OS e pro outro imovel meu').
"""
from __future__ import annotations

from typing import Any

from ondeline_api.adapters.sgp.base import EnderecoSgp
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
            "description": "Descricao curta do problema reportado pelo cliente.",
        },
        "endereco": {
            "type": "string",
            "description": (
                "Opcional. Endereco completo (rua, numero, bairro, cidade). "
                "Omita para usar o endereco do cadastro do cliente — que e o "
                "default. So passe se o cliente especificar outro endereco."
            ),
        },
    },
    "required": ["problema"],
}


def _fmt_endereco(e: EnderecoSgp) -> str:
    parts = [
        f"{e.logradouro}, {e.numero}".strip(", ") if e.logradouro else "",
        e.bairro,
        e.cidade + ("/" + e.uf if e.uf else ""),
    ]
    return " — ".join(p for p in parts if p)


def _split_endereco(endereco: str) -> tuple[str, str]:
    """Best-effort: extrai (rua, cidade) do texto livre."""
    parts = [p.strip() for p in (endereco or "").replace("—", ",").split(",") if p.strip()]
    rua = parts[0] if parts else ""
    cidade = parts[-2] if len(parts) >= 2 else (parts[-1] if parts else "")
    return rua, cidade


async def _resolve_endereco_do_cadastro(ctx: ToolContext) -> tuple[str, str, str]:
    """Returns (endereco_str, rua, cidade) lendo o SGP via cache.

    Fallback para Cliente.cidade do DB quando SGP indisponivel.
    """
    if ctx.cliente is None:
        return "", "", ""
    cidade_db = ctx.cliente.cidade or ""
    if ctx.sgp_cache is None:
        return cidade_db, "", cidade_db
    try:
        cpf = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
        cli_sgp = await ctx.sgp_cache.get_cliente(cpf)
    except Exception:
        return cidade_db, "", cidade_db
    if cli_sgp is None:
        return cidade_db, "", cidade_db
    end = (
        (cli_sgp.contratos[0].endereco if cli_sgp.contratos else None)
        or cli_sgp.endereco
    )
    endereco_str = _fmt_endereco(end) if end else cidade_db
    rua = (end.logradouro if end else "") or ""
    cidade = (end.cidade if end else "") or cidade_db
    return endereco_str, rua, cidade


@tool(
    name="abrir_ordem_servico",
    description=(
        "Cria uma Ordem de Servico (OS) tecnica para o cliente vinculado a esta conversa. "
        "Por padrao usa o endereco do cadastro do cliente para rotear o tecnico mais "
        "adequado por cidade/rua. Use quando o problema tecnico nao puder ser resolvido "
        "por orientacao."
    ),
    parameters=SCHEMA,
)
async def abrir_ordem_servico(
    ctx: ToolContext, *, problema: str, endereco: str | None = None
) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado"}

    if endereco:
        endereco_final = endereco
        rua, cidade = _split_endereco(endereco)
    else:
        endereco_final, rua, cidade = await _resolve_endereco_do_cadastro(ctx)
        if not endereco_final:
            return {
                "ok": False,
                "motivo": "endereco do cliente nao localizado no cadastro",
            }

    codigo = await next_codigo(ctx.session)
    tecnico = await TecnicoRepo(ctx.session).find_by_area(cidade=cidade, rua=rua)
    os_ = await OrdemServicoRepo(ctx.session).create(
        codigo=codigo,
        cliente_id=ctx.cliente.id,
        tecnico_id=tecnico.id if tecnico else None,
        problema=problema,
        endereco=endereco_final,
    )

    if tecnico is not None and tecnico.whatsapp:
        nome_cliente = (
            decrypt_pii(ctx.cliente.nome_encrypted)
            if ctx.cliente.nome_encrypted
            else "Cliente"
        )
        msg = (
            f"Nova OS {codigo}\n"
            f"Cliente: {nome_cliente}\n"
            f"Endereco: {endereco_final}\n"
            f"Problema: {problema}"
        )
        await ctx.evolution.send_text(tecnico.whatsapp, msg)

    return {
        "ok": True,
        "codigo": codigo,
        "tecnico_nome": tecnico.nome if tecnico else None,
        "tecnico_atribuido": tecnico is not None,
        "endereco_usado": endereco_final,
        "os_id": str(os_.id),
    }
