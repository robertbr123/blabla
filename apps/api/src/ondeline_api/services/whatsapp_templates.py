"""Registry de templates do WhatsApp Cloud API (Meta).

Mapeia ``NotificacaoTipo`` ao template aprovado no Meta Business + extrator
de body_params na ordem ``{{1}}, {{2}}, ...``.

IMPORTANTE: os ``name`` aqui sao apenas convencao — quem aprova de fato e o
Meta. Se o template real estiver com outro nome, troca aqui. Idioma sempre
``pt_BR``.

Pra canais Evolution, este registry NAO e usado — render_message() no
notify_sender ainda monta texto livre. Pra canais Cloud, ``send_one`` consulta
este registry primeiro e cai pra texto livre se nao houver spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from ondeline_api.db.models.business import Notificacao, NotificacaoTipo


@dataclass(frozen=True, slots=True)
class TemplateSpec:
    name: str
    language: str = "pt_BR"
    # Funcao que extrai os body params na ordem dos placeholders {{1}}, {{2}}...
    # Recebe (notificacao, primeiro_nome) — devolve lista de strings.
    body_params_fn: Callable[[Notificacao, str], list[str]] = lambda n, nome: []
    # Se o template tem header com media (boleto PDF, etc), extractor opcional.
    # Devolve (url, type) ou None.
    header_media_fn: Callable[[Notificacao], tuple[str, str] | None] | None = None


def _fmt_data(d: str) -> str:
    if d and "-" in d and len(d) >= 10:
        try:
            return datetime.fromisoformat(d[:10]).date().strftime("%d/%m/%Y")
        except ValueError:
            return d
    return d


def _fmt_valor(v: float | int | str) -> str:
    try:
        return f"{float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def _params_vencimento(n: Notificacao, nome: str) -> list[str]:
    titulos = (n.payload or {}).get("titulos") or []
    primeiro = titulos[0] if titulos else {}
    return [
        nome,
        _fmt_data(str(primeiro.get("vencimento", ""))),
        _fmt_valor(primeiro.get("valor", 0)),
    ]


def _params_atraso(n: Notificacao, nome: str) -> list[str]:
    payload = n.payload or {}
    return [nome, str(payload.get("dias_atraso", 0))]


def _params_pagamento(n: Notificacao, nome: str) -> list[str]:
    return [nome]


def _params_os_concluida(n: Notificacao, nome: str) -> list[str]:
    payload = n.payload or {}
    return [
        nome,
        str(payload.get("codigo", "")),
        str(payload.get("problema", "")) or "atendimento",
    ]


def _params_manutencao(n: Notificacao, nome: str) -> list[str]:
    payload = n.payload or {}
    titulo = str(payload.get("titulo", "manutencao programada"))
    inicio = payload.get("inicio_at", "")
    fim = payload.get("fim_at", "")
    try:
        janela = (
            f"{datetime.fromisoformat(inicio).strftime('%H:%M')}-"
            f"{datetime.fromisoformat(fim).strftime('%H:%M')}"
        )
    except (ValueError, TypeError):
        janela = "em breve"
    return [nome, titulo, janela]


# ─────────────────────────────────────────────────────────────
# Registry — mantenha sincronizado com os templates aprovados no Meta.
# ─────────────────────────────────────────────────────────────

TEMPLATE_BY_TIPO: dict[NotificacaoTipo, TemplateSpec] = {
    NotificacaoTipo.VENCIMENTO: TemplateSpec(
        name="fatura_vencendo",
        body_params_fn=_params_vencimento,
    ),
    NotificacaoTipo.ATRASO: TemplateSpec(
        name="fatura_vencida",
        body_params_fn=_params_atraso,
    ),
    NotificacaoTipo.PAGAMENTO: TemplateSpec(
        name="pagamento_confirmado",
        body_params_fn=_params_pagamento,
    ),
    NotificacaoTipo.OS_CONCLUIDA: TemplateSpec(
        name="os_concluida_csat",
        body_params_fn=_params_os_concluida,
    ),
    NotificacaoTipo.MANUTENCAO: TemplateSpec(
        name="manutencao_programada",
        body_params_fn=_params_manutencao,
    ),
}


def spec_for(tipo: NotificacaoTipo) -> TemplateSpec | None:
    return TEMPLATE_BY_TIPO.get(tipo)
