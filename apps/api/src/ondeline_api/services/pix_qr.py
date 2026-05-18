"""F3 — Geracao de QR Code Pix + cache + envio via Evolution.

Fluxo:
  1. Se a fatura tem `codigo_pix` (do SGP), usa esse BR Code direto.
  2. Caso contrario, le `pix.chave / pix.nome_beneficiario / pix.cidade_beneficiario`
     do Config e gera BR Code estatico com valor pre-preenchido.
  3. Renderiza PNG do QR (cache Redis 1h por hash do BR Code).
  4. Envia (a) imagem QR, (b) texto Pix copia-e-cola.

Falha gracefulle: sem chave Pix configurada + sem codigo_pix do SGP → loga
metrica `pix_qr_source_total{fonte='indisponivel'}` e nao envia QR. Caller
ja mandou o PDF do boleto.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.db.models.business import Config
from ondeline_api.observability.metrics import pix_qr_source_total
from ondeline_api.services.pix_brcode import gerar_brcode

log = structlog.get_logger(__name__)

_CACHE_PREFIX = "pix_qr:"
_CACHE_TTL_SECONDS = 3600
_QR_BOX_SIZE = 8  # ~256px final
_QR_BORDER = 2


async def _load_pix_config(session: AsyncSession) -> dict[str, str] | None:
    """Le chave/nome/cidade do beneficiario da tabela `config`."""
    stmt = select(Config).where(Config.key.in_(["pix.chave", "pix.nome", "pix.cidade"]))
    rows = list((await session.execute(stmt)).scalars().all())
    cfg = {row.key: row.value for row in rows}

    def _str(v: Any) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k in ("value", "v"):
                if k in v and isinstance(v[k], str):
                    return v[k]
        return ""

    chave = _str(cfg.get("pix.chave"))
    nome = _str(cfg.get("pix.nome"))
    cidade = _str(cfg.get("pix.cidade"))
    if not chave or not nome or not cidade:
        return None
    return {"chave": chave, "nome": nome, "cidade": cidade}


def _render_qr_png(brcode: str) -> bytes:
    """Gera PNG do QR Code. ~5kb pra 256x256."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=_QR_BOX_SIZE,
        border=_QR_BORDER,
    )
    qr.add_data(brcode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _cached_qr_png(redis: Any, brcode: str) -> bytes:
    """Renderiza com cache Redis (1h). Fail-open: erro de Redis = renderiza."""
    if redis is None:
        return _render_qr_png(brcode)
    key = _CACHE_PREFIX + hashlib.sha256(brcode.encode("utf-8")).hexdigest()[:16]
    try:
        hit = await redis.get(key)
        if hit:
            return bytes(hit)
    except Exception:
        pass
    png = _render_qr_png(brcode)
    try:
        await redis.set(key, png, ex=_CACHE_TTL_SECONDS)
    except Exception:
        pass
    return png


async def resolver_brcode(
    *,
    session: AsyncSession | None,
    codigo_pix_sgp: str | None,
    valor: float,
    fatura_id: str,
) -> tuple[str | None, str]:
    """Decide o BR Code a usar. Retorna ``(brcode, fonte)``.

    fonte: 'sgp' | 'gerado' | 'indisponivel'.
    """
    if codigo_pix_sgp:
        return codigo_pix_sgp, "sgp"
    if session is None:
        return None, "indisponivel"
    cfg = await _load_pix_config(session)
    if cfg is None:
        return None, "indisponivel"
    brcode = gerar_brcode(
        chave=cfg["chave"],
        nome=cfg["nome"],
        cidade=cfg["cidade"],
        valor=valor,
        txid=fatura_id,
    )
    return brcode, "gerado"


async def enviar_pix_qr_best_effort(
    *,
    evolution: EvolutionAdapter,
    redis: Any,
    jid: str,
    codigo_pix_sgp: str | None,
    valor: float,
    fatura_id: str,
    session: AsyncSession | None = None,
) -> bool:
    """Envia QR PNG + Pix copia-e-cola. Best-effort: falhas nao propagam.

    Retorna True se enviou QR+texto, False caso indisponivel ou falhou.
    """
    brcode, fonte = await resolver_brcode(
        session=session,
        codigo_pix_sgp=codigo_pix_sgp,
        valor=valor,
        fatura_id=fatura_id,
    )
    pix_qr_source_total.labels(fonte=fonte).inc()
    if brcode is None:
        log.info("pix_qr.unavailable", jid=jid, fatura_id=fatura_id)
        return False

    try:
        png = await _cached_qr_png(redis, brcode)
        await evolution.send_media_bytes(
            jid,
            data=png,
            mediatype="image",
            mimetype="image/png",
            file_name="pix.png",
            caption="Aponte a câmera do app do seu banco aqui 👆",
        )
        await evolution.send_text(jid, brcode)
        return True
    except EvolutionError as e:
        log.warning("pix_qr.send_failed", jid=jid, error=str(e))
        return False
    except Exception as e:
        log.warning("pix_qr.render_failed", jid=jid, error=str(e))
        return False
