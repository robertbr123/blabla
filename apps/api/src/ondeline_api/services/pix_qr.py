"""F3 — Geração de QR Code Pix a partir do `codigo_pix` do SGP.

O BR Code SEMPRE vem do SGP — a conciliação do pagamento depende do `txid`
emitido pelo proprio SGP. Nao geramos BR Code proprio: cliente pagaria um
Pix que o SGP nao saberia atribuir.

Comportamento:
  - `codigo_pix` presente na fatura → renderiza QR PNG + envia + texto copia-e-cola
  - `codigo_pix` ausente → log warn + metrica `pix_qr_source_total{fonte='indisponivel'}`,
    nao envia QR. Caller ja mandou PDF do boleto.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

import structlog

from ondeline_api.adapters.evolution import EvolutionAdapter, EvolutionError
from ondeline_api.observability.metrics import pix_qr_source_total

log = structlog.get_logger(__name__)

_CACHE_PREFIX = "pix_qr:"
_CACHE_TTL_SECONDS = 3600
_QR_BOX_SIZE = 8  # ~256px final
_QR_BORDER = 2


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


async def enviar_pix_qr_best_effort(
    *,
    evolution: EvolutionAdapter,
    redis: Any,
    jid: str,
    codigo_pix_sgp: str | None,
    valor: float,  # mantido na assinatura por compatibilidade
    fatura_id: str,
    session: Any = None,  # mantido na assinatura por compatibilidade
) -> bool:
    """Envia QR PNG do BR Code do SGP + Pix copia-e-cola.

    Best-effort: erros de render/envio nao propagam. Retorna True so quando
    enviou QR + texto.
    """
    if not codigo_pix_sgp:
        pix_qr_source_total.labels(fonte="indisponivel").inc()
        log.warning(
            "pix_qr.sgp_sem_codigo",
            fatura_id=fatura_id,
            hint="Verifique a configuracao de Pix no SGP — fatura sem codigoPix.",
        )
        return False

    pix_qr_source_total.labels(fonte="sgp").inc()
    log.info(
        "pix_qr.start",
        jid=jid,
        fatura_id=fatura_id,
        brcode_len=len(codigo_pix_sgp),
    )

    # Sempre tenta enviar o texto copia-e-cola PRIMEIRO — eh o mais importante
    # e nao depende de gerar imagem. Se a imagem falhar, ao menos o codigo
    # textual chega ao cliente.
    text_ok = False
    try:
        await evolution.send_text(jid, codigo_pix_sgp)
        text_ok = True
        log.info("pix_qr.text_sent", jid=jid)
    except EvolutionError as e:
        log.warning("pix_qr.text_send_failed", jid=jid, error=str(e))
    except Exception as e:
        log.warning("pix_qr.text_send_failed_unexpected", jid=jid, error=str(e))

    # Depois tenta a imagem QR (best-effort, opcional).
    img_ok = False
    try:
        png = await _cached_qr_png(redis, codigo_pix_sgp)
        log.info("pix_qr.png_rendered", jid=jid, bytes=len(png))
        await evolution.send_media_bytes(
            jid,
            data=png,
            mediatype="image",
            mimetype="image/png",
            file_name="pix.png",
            caption="Aponte a câmera do app do seu banco aqui 👆",
        )
        img_ok = True
        log.info("pix_qr.png_sent", jid=jid)
    except EvolutionError as e:
        log.warning("pix_qr.png_send_failed", jid=jid, error=str(e))
    except Exception as e:
        log.warning("pix_qr.png_render_failed", jid=jid, error=str(e))

    return text_ok or img_ok
