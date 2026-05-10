"""Tool: envia ate N boletos em aberto via Evolution sendMedia.

Le titulos do cache (ou consulta SGP se cache stale via invalidate). Para
cada titulo: envia PDF (link da SGP) + uma mensagem extra com codigoPix.
Invalida cache de cliente apos envio (proxima consulta busca SGP novamente).
"""
from __future__ import annotations

from typing import Any

from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_boletos": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 3,
        }
    },
}


def _fmt_data(d: str) -> str:
    if d and "-" in d and len(d) == 10:
        y, m, day = d.split("-")
        return f"{day}/{m}/{y}"
    return d


def _build_caption(idx: int, total: int, t: Fatura) -> str:
    venc = _fmt_data(t.vencimento)
    valor = f"R$ {t.valor:.2f}".replace(".", ",")
    cap = (
        f"Fatura {idx + 1} de {total}\n"
        f"Vencimento: {venc}\n"
        f"Valor: {valor}"
    )
    if t.dias_atraso > 0:
        cap += f"\nAtenção: {t.dias_atraso} dia(s) em atraso"
    return cap


@tool(
    name="enviar_boleto",
    description=(
        "Envia ate `max_boletos` faturas em aberto do cliente vinculado a esta "
        "conversa, via PDF + codigo PIX. Use quando o cliente pedir boleto, "
        "fatura, 2a via ou PIX."
    ),
    parameters=SCHEMA,
)
async def enviar_boleto(ctx: ToolContext, *, max_boletos: int = 3) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado a esta conversa"}

    # Recuperamos o ClienteSgp pelo cache via cpf cleartext (decrypt do Cliente).
    cpf_clean = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_clean)
    if cli_sgp is None:
        return {"ok": False, "motivo": "cliente nao localizado no SGP"}

    abertos = [t for t in cli_sgp.titulos if t.status == "aberto"]
    if not abertos:
        return {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}

    enviados = 0
    vencimentos: list[str] = []
    n = min(len(abertos), max(1, min(max_boletos, 5)))

    for i, t in enumerate(abertos[:n]):
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

    # invalida cache pra proxima consulta refletir status atualizado
    await ctx.sgp_cache.invalidate(cpf_clean)
    return {"ok": True, "enviados": enviados, "vencimentos": vencimentos}
