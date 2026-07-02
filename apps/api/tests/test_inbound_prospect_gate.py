"""Gate de identificacao x fluxo de lead (prospect que quer contratar).

Regressao: o gate barrava a resposta com o NOME do interessado (nao casava
CPF/opcao/palavra-chave), repetindo 'digite seu CPF' e nunca registrando o
lead. Uma vez que o prospect declara intencao de contratar, a conversa entra
em LEAD_INTERESSE — que NAO passa pelo gate.
"""
from __future__ import annotations

from ondeline_api.db.models.business import ConversaEstado
from ondeline_api.services.inbound import _GATE_ESTADOS, _is_prospect_intent


def test_lead_states_fora_do_gate() -> None:
    assert ConversaEstado.LEAD_INTERESSE not in _GATE_ESTADOS
    assert ConversaEstado.LEAD_NOME not in _GATE_ESTADOS


def test_prospect_intent_reconhece_contratar() -> None:
    assert _is_prospect_intent("2") is True
    assert _is_prospect_intent("quero contratar") is True
    assert _is_prospect_intent("quero um plano") is True
    assert _is_prospect_intent("quero o plano premium") is True


def test_prospect_intent_ignora_ja_cliente_e_nome() -> None:
    assert _is_prospect_intent("1") is False
    assert _is_prospect_intent("ja sou cliente") is False
    # O nome do interessado NAO e intencao — mas tambem nao deve ser barrado,
    # pois quando ele responde o nome a conversa ja esta em LEAD_INTERESSE.
    assert _is_prospect_intent("Robert Albino Braga") is False
    assert _is_prospect_intent("") is False
