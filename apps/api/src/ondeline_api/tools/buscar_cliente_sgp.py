"""Tool: busca cliente nos provedores SGP via cache.

Atualiza o `Cliente` no DB e vincula `Conversa.cliente_id`. Retorna dict
mascarado para o LLM (nao vaza CPF, mantem nome/plano/status/cidade,
proxima fatura, e lista resumida de contratos quando houver mais de um).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from ondeline_api.adapters.sgp.base import Contrato, Fatura
from ondeline_api.repositories.cliente import ClienteRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


def _today() -> date:
    return datetime.now(tz=UTC).date()

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cpf_cnpj": {
            "type": "string",
            "description": "CPF ou CNPJ; pontuacao opcional (sera limpa).",
        }
    },
    "required": ["cpf_cnpj"],
}


_SUSPENSO_TOKENS = ("suspenso", "bloqueado", "inadimplente", "cancelado")


def _is_suspenso(status: str | None) -> bool:
    s = (status or "").strip().lower()
    return any(tok in s for tok in _SUSPENSO_TOKENS)


def _vencimento_date(t: Fatura) -> date | None:
    if not t.vencimento:
        return None
    try:
        return datetime.fromisoformat(t.vencimento).date()
    except ValueError:
        return None


def _is_overdue(t: Fatura, today: date) -> bool:
    v = _vencimento_date(t)
    return v is not None and v < today


def _proxima_fatura(titulos: list[Fatura], today: date) -> Fatura | None:
    """Mais antiga em atraso > vencimento futuro mais proximo.

    Confiavel: usa data de vencimento, NAO t.dias_atraso (alguns SGPs retornam
    esse campo invertido/inconsistente).
    """
    abertos = [t for t in titulos if t.status == "aberto" and t.vencimento]
    if not abertos:
        return None
    atrasados = sorted(
        (t for t in abertos if _is_overdue(t, today)),
        key=lambda t: t.vencimento,  # ASC: mais antiga primeiro
    )
    if atrasados:
        return atrasados[0]
    futuros = sorted(
        (t for t in abertos if not _is_overdue(t, today)),
        key=lambda t: t.vencimento,
    )
    return futuros[0] if futuros else None


def _resumo_titulos(titulos: list[Fatura]) -> dict[str, Any]:
    today = _today()
    abertos = [t for t in titulos if t.status == "aberto"]
    prox = _proxima_fatura(titulos, today)
    return {
        "abertos": len(abertos),
        "atrasados": sum(1 for t in abertos if _is_overdue(t, today)),
        "vencimentos": [t.vencimento for t in abertos[:3]],
        "proximo_vencimento": prox.vencimento if prox else None,
        "proximo_valor": prox.valor if prox else None,
    }


def _resumo_contrato(c: Contrato) -> dict[str, Any]:
    return {
        "id": c.id,
        "plano": c.plano,
        "status": c.status,
        "cidade": c.cidade,
        "suspenso": _is_suspenso(c.status),
    }


@tool(
    name="buscar_cliente_sgp",
    description=(
        "Consulta cliente nos provedores SGP (Ondeline + LinkNetAM, nessa ordem). "
        "Use quando o cliente informar CPF ou CNPJ. Retorna nome, plano principal, "
        "status, cidade, proxima fatura, e lista de contratos quando o cliente "
        "tiver mais de um contrato (para o bot oferecer escolha)."
    ),
    parameters=SCHEMA,
)
async def buscar_cliente_sgp(ctx: ToolContext, *, cpf_cnpj: str) -> dict[str, Any]:
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_cnpj)
    if cli_sgp is None:
        return {"encontrado": False}

    cliente_db = await ClienteRepo(ctx.session).upsert_from_sgp(
        cli_sgp, whatsapp=ctx.conversa.whatsapp
    )
    ctx.conversa.cliente_id = cliente_db.id
    await ctx.session.flush()

    contratos = cli_sgp.contratos or []
    contrato_principal = contratos[0] if contratos else None
    result: dict[str, Any] = {
        "encontrado": True,
        "nome": cli_sgp.nome,
        "plano": contrato_principal.plano if contrato_principal else None,
        "status_contrato": contrato_principal.status if contrato_principal else None,
        "motivo_status": contrato_principal.motivo_status if contrato_principal else None,
        "cidade": (
            contrato_principal.cidade
            if contrato_principal and contrato_principal.cidade
            else cli_sgp.endereco.cidade
        ),
        "suspenso": _is_suspenso(
            contrato_principal.status if contrato_principal else None
        ),
        "faturas": _resumo_titulos(cli_sgp.titulos),
    }
    if len(contratos) > 1:
        result["contratos"] = [_resumo_contrato(c) for c in contratos]
        result["multiplos_contratos"] = True
    return result
