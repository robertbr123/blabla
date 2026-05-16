"""Tool: envia 1 boleto especifico (ou poucos) via Evolution sendMedia.

Le titulos do cache (ou consulta SGP via invalidate). Por padrao manda APENAS
1 boleto — o mais relevante: atrasado mais antigo, ou do mes atual. O LLM pode
pedir um mes especifico via parametro `mes` (ex: "atual", "proximo", "atrasado",
"2026-05", "outubro"). Invalida cache de cliente apos envio.
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mes": {
            "type": "string",
            "description": (
                "Mes-alvo da fatura. Aceita: 'atual' (default), 'proximo', "
                "'atrasado' (a mais antiga em atraso), 'YYYY-MM' (ex 2026-05), "
                "ou nome do mes em portugues (ex 'outubro'). Omita para "
                "deixar a tool escolher: atrasada mais antiga > mes corrente > proxima."
            ),
        },
        "max_boletos": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 1,
            "description": "Quantos boletos enviar (1-5). Default 1.",
        },
    },
}


_MESES_PT: dict[str, int] = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def _today() -> date:
    return datetime.now(tz=UTC).date()


def _parse_mes_alvo(mes: str | None, today: date) -> tuple[int, int] | None:
    """Returns (year, month) target or None when no specific month is requested.

    Falsy/empty/'atual' -> mes corrente.
    'proximo' -> mes seguinte.
    'atrasado' / 'atrasada' -> sentinel signaling 'pick most overdue'.
    'YYYY-MM' -> direct.
    'outubro' / 'out' -> mes pelo nome (ano corrente).
    """
    if not mes:
        return today.year, today.month
    m = mes.strip().lower()
    if m in ("atual", "agora", "este mes", "este mês", "do mes", "do mês"):
        return today.year, today.month
    if m in ("proximo", "próximo", "proxima", "próxima", "que vem", "seguinte"):
        nxt = (today.month % 12) + 1
        year = today.year + (1 if today.month == 12 else 0)
        return year, nxt
    if m in ("atrasado", "atrasada", "atrasadas", "em atraso"):
        return None  # sinaliza "pegar mais atrasada"
    iso = re.match(r"^(\d{4})-(\d{1,2})$", m)
    if iso:
        return int(iso.group(1)), int(iso.group(2))
    br = re.match(r"^(\d{1,2})/(\d{4})$", m)
    if br:
        return int(br.group(2)), int(br.group(1))
    if m in _MESES_PT:
        return today.year, _MESES_PT[m]
    return today.year, today.month  # fallback seguro


def _fatura_year_month(t: Fatura) -> tuple[int, int] | None:
    v = (t.vencimento or "")[:7]
    try:
        y, m = v.split("-")
        return int(y), int(m)
    except (ValueError, AttributeError):
        return None


def _is_overdue(t: Fatura, today: date) -> bool:
    """Confiavel: usa data de vencimento. NAO confiar em t.dias_atraso porque
    alguns SGPs devolvem o campo com semantica inconsistente.
    """
    if not t.vencimento:
        return False
    try:
        v = datetime.fromisoformat(t.vencimento).date()
    except ValueError:
        return False
    return v < today


def _escolher_faturas(
    abertos: list[Fatura], mes: str | None, max_boletos: int
) -> list[Fatura]:
    today = _today()
    alvo = _parse_mes_alvo(mes, today)
    # atrasadas ordenadas pela DATA de vencimento (mais antiga primeiro)
    overdue_sorted = sorted(
        (t for t in abertos if _is_overdue(t, today)),
        key=lambda t: t.vencimento,
    )
    if alvo is None:  # explicitamente pediu 'atrasado'
        candidatos = overdue_sorted
    elif mes:
        candidatos = [t for t in abertos if _fatura_year_month(t) == alvo]
    elif max_boletos > 1:
        # cliente pediu mais de 1 sem mes: devolve todas, atrasadas primeiro
        nao_atrasadas = [t for t in abertos if not _is_overdue(t, today)]
        candidatos = overdue_sorted + sorted(nao_atrasadas, key=lambda t: t.vencimento or "")
    else:
        # default: 1 fatura, prioriza atrasada mais antiga > mes atual > primeira aberta por data
        candidatos = (
            overdue_sorted
            or [t for t in abertos if _fatura_year_month(t) == alvo]
            or sorted(abertos, key=lambda t: t.vencimento or "")
        )
    return candidatos[: max(1, min(max_boletos, 5))]


def _fmt_data(d: str) -> str:
    if d and "-" in d and len(d) == 10:
        y, m, day = d.split("-")
        return f"{day}/{m}/{y}"
    return d


def _dias_atraso_real(t: Fatura, today: date) -> int:
    """Calcula atraso a partir da data de vencimento — ignora t.dias_atraso
    porque alguns SGPs retornam esse campo com semantica inconsistente.
    """
    if not t.vencimento:
        return 0
    try:
        v = datetime.fromisoformat(t.vencimento).date()
    except ValueError:
        return 0
    delta = (today - v).days
    return max(0, delta)


def _build_caption(idx: int, total: int, t: Fatura) -> str:
    venc = _fmt_data(t.vencimento)
    valor = f"R$ {t.valor:.2f}".replace(".", ",")
    if total > 1:
        cap = f"Fatura {idx + 1} de {total}\nVencimento: {venc}\nValor: {valor}"
    else:
        cap = f"Vencimento: {venc}\nValor: {valor}"
    atraso = _dias_atraso_real(t, _today())
    if atraso > 0:
        cap += f"\nAtenção: {atraso} dia(s) em atraso"
    return cap


@tool(
    name="enviar_boleto",
    description=(
        "Envia 1 fatura especifica (ou poucas) do cliente vinculado a esta "
        "conversa via PDF + codigo PIX. Por padrao manda apenas 1: a atrasada "
        "mais antiga ou a do mes corrente. Use o parametro `mes` quando o "
        "cliente especificar (ex: 'fatura de outubro', 'do proximo mes', 'a atrasada')."
    ),
    parameters=SCHEMA,
)
async def enviar_boleto(
    ctx: ToolContext, *, mes: str | None = None, max_boletos: int = 1
) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado a esta conversa"}

    cpf_clean = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_clean)
    if cli_sgp is None:
        return {"ok": False, "motivo": "cliente nao localizado no SGP"}

    abertos = [t for t in cli_sgp.titulos if t.status == "aberto"]
    if not abertos:
        return {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}

    escolhidos = _escolher_faturas(abertos, mes, max_boletos)
    if not escolhidos:
        # nenhuma fatura para o mes pedido — devolve catalogo para o LLM oferecer
        return {
            "ok": True,
            "enviados": 0,
            "mensagem": f"Nao encontrei fatura aberta para '{mes}'.",
            "meses_disponiveis": sorted(
                {t.vencimento[:7] for t in abertos if t.vencimento}
            ),
        }

    enviados = 0
    vencimentos: list[str] = []
    n = len(escolhidos)
    for i, t in enumerate(escolhidos):
        if t.link_pdf:
            await ctx.evolution.send_media(
                ctx.conversa.whatsapp,
                url=t.link_pdf,
                mediatype="document",
                mimetype="application/pdf",
                file_name=f"fatura_{t.vencimento or i + 1}.pdf",
                caption=_build_caption(i, n, t),
            )
            enviados += 1
            vencimentos.append(t.vencimento)
        if t.codigo_pix:
            await ctx.evolution.send_text(ctx.conversa.whatsapp, t.codigo_pix)

    await ctx.sgp_cache.invalidate(cpf_clean)
    return {"ok": True, "enviados": enviados, "vencimentos": vencimentos}
