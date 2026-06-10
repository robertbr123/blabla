"""Guards do llm_turn: status da conversa + ultima mensagem."""
from __future__ import annotations

from ondeline_api.db.models.business import ConversaStatus, MensagemRole
from ondeline_api.workers.llm_turn import _skip_reason


def test_roda_quando_bot_e_ultima_msg_cliente() -> None:
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.CLIENTE) is None


def test_skip_quando_humano_assumiu() -> None:
    assert _skip_reason(ConversaStatus.HUMANO, MensagemRole.CLIENTE) == "status_humano"


def test_skip_quando_aguardando_atendente() -> None:
    assert _skip_reason(ConversaStatus.AGUARDANDO, MensagemRole.CLIENTE) == "status_aguardando"


def test_skip_quando_encerrada() -> None:
    assert _skip_reason(ConversaStatus.ENCERRADA, MensagemRole.CLIENTE) == "status_encerrada"


def test_skip_quando_bot_ja_respondeu() -> None:
    # turno requeued chegou depois do turno anterior ja ter coberto a msg
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.BOT) == "ja_respondida"
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.ATENDENTE) == "ja_respondida"


def test_roda_em_conversa_sem_mensagens() -> None:
    # defensivo: sem historico nao bloqueia (caso teorico)
    assert _skip_reason(ConversaStatus.BOT, None) is None
