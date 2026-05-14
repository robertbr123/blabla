"""Geração de PDF para Ordens de Serviço com WeasyPrint."""
from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from ondeline_api.db.models.business import OrdemServico

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(UTC).strftime("%d/%m/%Y %H:%M")


_FOTOS_DIR = Path("/tmp/ondeline_os_fotos")


def _load_fotos(os_: OrdemServico) -> list[dict]:
    fotos = []
    for meta in os_.fotos or []:
        path = Path(meta.get("url", ""))
        if not path.is_relative_to(_FOTOS_DIR) or not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode()
        fotos.append(
            {
                "b64": b64,
                "mime": meta.get("mime", "image/jpeg"),
                "ts": _fmt_dt(datetime.fromisoformat(meta["ts"])) if meta.get("ts") else "",
            }
        )
    return fotos


def generate_os_pdf(
    os_: OrdemServico,
    cliente_nome: str | None,
    cliente_whatsapp: str | None,
    tecnico_nome: str | None,
    tecnico_whatsapp: str | None,
) -> bytes:
    """Renderiza template HTML e converte para PDF em memória. Retorna bytes do PDF."""
    template = _jinja_env.get_template("os_pdf.html")
    fotos = _load_fotos(os_)

    os_data = {
        "codigo": os_.codigo,
        "status": os_.status.value,
        "problema": os_.problema,
        "endereco": os_.endereco,
        "criada_em": _fmt_dt(os_.criada_em),
        "concluida_em": _fmt_dt(os_.concluida_em),
        "agendamento_at": _fmt_dt(os_.agendamento_at),
        "csat": os_.csat,
        "comentario_cliente": os_.comentario_cliente,
    }

    html_content = template.render(
        os=os_data,
        cliente_nome=cliente_nome,
        cliente_whatsapp=cliente_whatsapp,
        tecnico_nome=tecnico_nome,
        tecnico_whatsapp=tecnico_whatsapp,
        fotos=fotos,
        gerado_em=datetime.now(tz=UTC).strftime("%d/%m/%Y %H:%M"),
    )

    return HTML(string=html_content, base_url=str(_TEMPLATES_DIR)).write_pdf()
