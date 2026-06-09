"""Horário comercial do atendimento humano.

Gating leve: o bot continua respondendo 24/7, mas FORA do expediente as mensagens
de hand-off informam a janela de atendimento e o retorno no próximo horário
comercial — em vez de prometer atendimento humano imediato.

Config via Settings (env), timezone fixo America/Sao_Paulo. `business_days` em ISO
(Seg=1 … Dom=7). Fail-open: config inválida ou gating desligado => sempre "aberto"
(mantém o comportamento atual, nunca silencia o bot).
"""
from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import structlog

from ondeline_api.config import get_settings

log = structlog.get_logger(__name__)

_TZ = ZoneInfo("America/Sao_Paulo")
_DEFAULT_DAYS = {1, 2, 3, 4, 5}
_DEFAULT_START = time(8, 0)
_DEFAULT_END = time(18, 0)
_DIAS_PT = {
    1: "segunda",
    2: "terça",
    3: "quarta",
    4: "quinta",
    5: "sexta",
    6: "sábado",
    7: "domingo",
}


def _parse_hhmm(value: str, fallback: time) -> time:
    try:
        h, m = value.strip().split(":")
        return time(int(h), int(m))
    except Exception:
        log.warning("business_hours.invalid_time", value=value)
        return fallback


def _parse_days(value: str) -> set[int]:
    try:
        days = {int(x) for x in value.split(",") if x.strip()}
        valid = {d for d in days if 1 <= d <= 7}
        return valid or set(_DEFAULT_DAYS)
    except Exception:
        log.warning("business_hours.invalid_days", value=value)
        return set(_DEFAULT_DAYS)


def is_open(now: datetime | None = None) -> bool:
    """True se estamos dentro do horário comercial (America/Sao_Paulo).

    Gating desligado (`business_hours_enabled=False`) => sempre True.
    """
    s = get_settings()
    if not s.business_hours_enabled:
        return True
    now = now or datetime.now(tz=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local = now.astimezone(_TZ)
    start = _parse_hhmm(s.business_hours_start, _DEFAULT_START)
    end = _parse_hhmm(s.business_hours_end, _DEFAULT_END)
    days = _parse_days(s.business_days)
    return local.isoweekday() in days and start <= local.time() < end


def janela_descricao() -> str:
    """Descrição textual da janela, ex: 'segunda a sexta, das 08:00 às 18:00'."""
    s = get_settings()
    days = sorted(_parse_days(s.business_days))
    start = _parse_hhmm(s.business_hours_start, _DEFAULT_START)
    end = _parse_hhmm(s.business_hours_end, _DEFAULT_END)
    if days and days == list(range(days[0], days[-1] + 1)) and len(days) > 1:
        dias_txt = f"{_DIAS_PT[days[0]]} a {_DIAS_PT[days[-1]]}"
    else:
        dias_txt = ", ".join(_DIAS_PT[d] for d in days)
    return f"{dias_txt}, das {start.strftime('%H:%M')} às {end.strftime('%H:%M')}"


def closed_notice() -> str:
    """Frase de expectativa enviada ao cliente fora do expediente (sem saudação)."""
    return (
        f"No momento estamos fora do horário de atendimento (atendimento humano: "
        f"{janela_descricao()}). Sua mensagem foi registrada e um atendente retorna "
        "no próximo horário comercial. 🕐"
    )


def handoff_phrase() -> str:
    """Frase de 'aguarde atendente' apropriada ao horário (aberto vs fechado)."""
    if is_open():
        return "Em breve um atendente retorna por aqui. 🙏"
    return closed_notice()


def humano_message(open_msg: str, *, closed_prefix: str = "") -> str:
    """Mensagem de hand-off para humano, ciente do horário.

    Dentro do expediente devolve ``open_msg`` (o texto atual, que pode prometer
    atendimento imediato). Fora do expediente devolve ``closed_prefix`` seguido do
    aviso de fechado — ou só o aviso, se ``closed_prefix`` for vazio.
    """
    if is_open():
        return open_msg
    if closed_prefix:
        return f"{closed_prefix} {closed_notice()}"
    return closed_notice()


def llm_prompt_hint() -> str | None:
    """Linha a injetar no system prompt do LLM quando fora do expediente, ou None."""
    if is_open():
        return None
    return (
        f"ATENÇÃO: agora está FORA do horário comercial (atendimento humano: "
        f"{janela_descricao()}). Ao transferir para um atendente humano, avise que "
        "ele retorna no próximo horário comercial; NÃO prometa atendimento imediato."
    )
