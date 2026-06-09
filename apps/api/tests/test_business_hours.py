"""Testes do gating de horário comercial (services/business_hours).

America/Sao_Paulo = UTC-3 (sem DST desde 2019). Os datetimes abaixo são UTC;
o horário local de SP é UTC menos 3h.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ondeline_api.services import business_hours as bh


class _FakeSettings:
    business_hours_enabled = True
    business_hours_start = "08:00"
    business_hours_end = "18:00"
    business_days = "1,2,3,4,5"  # Seg-Sex (Seg=1..Sex=5)


@pytest.fixture
def default_hours(monkeypatch):
    monkeypatch.setattr(bh, "get_settings", lambda: _FakeSettings())


# 2026-06-09 = terça (dia útil); 2026-06-13 = sábado.
TUE = lambda h, m=0: datetime(2026, 6, 9, h, m, tzinfo=UTC)  # noqa: E731
SAT = lambda h, m=0: datetime(2026, 6, 13, h, m, tzinfo=UTC)  # noqa: E731


def test_aberto_meio_do_expediente(default_hours):
    # Ter 10:00 BRT = 13:00 UTC
    assert bh.is_open(TUE(13)) is True


def test_fechado_antes_do_inicio(default_hours):
    # Ter 07:59 BRT = 10:59 UTC
    assert bh.is_open(TUE(10, 59)) is False


def test_borda_inicio_inclusiva(default_hours):
    # Ter 08:00 BRT = 11:00 UTC → aberto
    assert bh.is_open(TUE(11)) is True


def test_borda_fim_exclusiva(default_hours):
    # Ter 18:00 BRT = 21:00 UTC → fechado (fim exclusivo)
    assert bh.is_open(TUE(21)) is False
    # Ter 17:59 BRT = 20:59 UTC → ainda aberto
    assert bh.is_open(TUE(20, 59)) is True


def test_fim_de_semana_fechado(default_hours):
    # Sáb 10:00 BRT = 13:00 UTC
    assert bh.is_open(SAT(13)) is False


def test_disabled_sempre_aberto(monkeypatch):
    class _Off(_FakeSettings):
        business_hours_enabled = False

    monkeypatch.setattr(bh, "get_settings", lambda: _Off())
    # Sábado de madrugada, mas gating desligado → aberto
    assert bh.is_open(SAT(5)) is True


def test_now_naive_tratado_como_utc(default_hours):
    naive = datetime(2026, 6, 9, 13, 0)  # sem tz → assume UTC → 10h BRT
    assert bh.is_open(naive) is True


def test_closed_notice_reflete_janela(default_hours):
    txt = bh.closed_notice()
    assert "segunda a sexta" in txt
    assert "08:00" in txt and "18:00" in txt


def test_handoff_phrase_varia_por_horario(default_hours, monkeypatch):
    monkeypatch.setattr(bh, "is_open", lambda now=None: True)
    assert "Em breve" in bh.handoff_phrase()
    monkeypatch.setattr(bh, "is_open", lambda now=None: False)
    assert "próximo horário comercial" in bh.handoff_phrase()


def test_humano_message_aberto_vs_fechado(default_hours, monkeypatch):
    monkeypatch.setattr(bh, "is_open", lambda now=None: True)
    assert bh.humano_message("texto aberto", closed_prefix="px") == "texto aberto"
    monkeypatch.setattr(bh, "is_open", lambda now=None: False)
    fechado = bh.humano_message("texto aberto", closed_prefix="Vou te transferir.")
    assert "texto aberto" not in fechado
    assert fechado.startswith("Vou te transferir.")
    assert "próximo horário comercial" in fechado
    # sem prefixo → só o aviso de fechado
    assert bh.humano_message("aberto") == bh.closed_notice()


def test_llm_hint_none_quando_aberto(default_hours, monkeypatch):
    monkeypatch.setattr(bh, "is_open", lambda now=None: True)
    assert bh.llm_prompt_hint() is None
    monkeypatch.setattr(bh, "is_open", lambda now=None: False)
    hint = bh.llm_prompt_hint()
    assert hint is not None and "NÃO prometa atendimento imediato" in hint
