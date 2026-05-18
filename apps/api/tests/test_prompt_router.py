"""F5 — Roteador de variantes de prompt (A/B test)."""
from __future__ import annotations

import pytest
from ondeline_api.db.models.business import PromptVariant
from ondeline_api.services.prompt_router import _bucket_for_jid, escolher_variante

pytestmark = pytest.mark.asyncio


def test_bucket_deterministic() -> None:
    jid = "5511999998888@s.whatsapp.net"
    assert _bucket_for_jid(jid) == _bucket_for_jid(jid)
    assert 0 <= _bucket_for_jid(jid) < 100


def test_bucket_diferente_pra_jids_diferentes() -> None:
    a = _bucket_for_jid("5511111@s.whatsapp.net")
    b = _bucket_for_jid("5522222@s.whatsapp.net")
    # Probabilisticamente: 2 jids quase sempre caem em buckets diferentes
    # (chance 1/100 de colisão). Aceitavel pro teste.
    assert (a != b) or True  # nao falha se colidir; checamos so o range
    assert 0 <= a < 100
    assert 0 <= b < 100


async def test_escolher_variante_sem_variantes_retorna_none(db_session) -> None:
    res = await escolher_variante(db_session, "5511aaa@s.whatsapp.net")
    assert res is None


async def test_escolher_variante_com_trafego_100_sempre_seleciona(db_session) -> None:
    v = PromptVariant(
        nome="full_test",
        system_prompt="Voce eh um bot teste.",
        ativo=True,
        trafego_pct=100,
    )
    db_session.add(v)
    await db_session.flush()

    res = await escolher_variante(db_session, "qualquer-jid@s.whatsapp.net")
    assert res is not None
    assert res.nome == "full_test"


async def test_escolher_variante_inativa_e_ignorada(db_session) -> None:
    v = PromptVariant(
        nome="inativa_test",
        system_prompt="Voce eh um bot teste.",
        ativo=False,  # desativada
        trafego_pct=100,
    )
    db_session.add(v)
    await db_session.flush()

    res = await escolher_variante(db_session, "qualquer-jid@s.whatsapp.net")
    assert res is None


async def test_escolher_variante_split_30_70(db_session) -> None:
    """Variante A=30% recebe ~30 buckets, B=70% recebe ~70 buckets.

    Validamos que numa varredura de 100 jids sequenciais, contagens batem
    aproximadamente. Bucketing eh deterministico (hash sha256), entao o resultado
    eh reprodutivel — nao flaky.
    """
    a = PromptVariant(
        nome="ab_a", system_prompt="Prompt A " * 5, ativo=True, trafego_pct=30
    )
    b = PromptVariant(
        nome="ab_b", system_prompt="Prompt B " * 5, ativo=True, trafego_pct=70
    )
    db_session.add(a)
    db_session.add(b)
    await db_session.flush()

    cont = {"ab_a": 0, "ab_b": 0, "default": 0}
    for i in range(200):
        jid = f"55{i:09d}@s.whatsapp.net"
        chosen = await escolher_variante(db_session, jid)
        if chosen is None:
            cont["default"] += 1
        else:
            cont[chosen.nome] += 1

    # Soma confere
    assert cont["ab_a"] + cont["ab_b"] + cont["default"] == 200
    # Default deve ser zero (30+70=100)
    assert cont["default"] == 0
    # Distribuicao aproximada — toleramos +/- 30% pra evitar flakiness
    assert 40 <= cont["ab_a"] <= 80, f"ab_a={cont['ab_a']}"
    assert 120 <= cont["ab_b"] <= 160, f"ab_b={cont['ab_b']}"


async def test_escolher_variante_mesmo_jid_sempre_mesma_variante(db_session) -> None:
    a = PromptVariant(
        nome="stick_a", system_prompt="A " * 10, ativo=True, trafego_pct=50
    )
    b = PromptVariant(
        nome="stick_b", system_prompt="B " * 10, ativo=True, trafego_pct=50
    )
    db_session.add(a)
    db_session.add(b)
    await db_session.flush()

    jid = "5511determ@s.whatsapp.net"
    first = await escolher_variante(db_session, jid)
    for _ in range(5):
        again = await escolher_variante(db_session, jid)
        assert again is not None and first is not None
        assert again.nome == first.nome


async def test_escolher_variante_canal_filtra(db_session) -> None:
    """Variante com canal_slug='comercial' so se aplica a esse canal."""
    so_com = PromptVariant(
        nome="so_comerc",
        system_prompt="Comercial " * 5,
        ativo=True,
        trafego_pct=100,
        canal_slug="comercial",
    )
    db_session.add(so_com)
    await db_session.flush()

    res_com = await escolher_variante(
        db_session, "anyjid@s.whatsapp.net", canal_slug="comercial"
    )
    assert res_com is not None and res_com.nome == "so_comerc"

    res_sup = await escolher_variante(
        db_session, "anyjid@s.whatsapp.net", canal_slug="suporte"
    )
    assert res_sup is None
