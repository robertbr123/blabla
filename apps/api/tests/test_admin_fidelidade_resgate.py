"""Admin de resgates de fidelidade — deve mostrar quem e o cliente.

Regressao: a lista de resgates so devolvia o UUID do cliente_app_user, entao
o admin nao conseguia saber quem pediu o resgate.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ondeline_api.api.v1.cliente_app_fidelidade import _admin_resgate_out
from ondeline_api.db.crypto import encrypt_pii
from ondeline_api.db.models.cliente_app import (
    ClienteAppFidelidadeResgate,
    ClienteAppUser,
)


def _resgate(user_id) -> ClienteAppFidelidadeResgate:
    return ClienteAppFidelidadeResgate(
        id=uuid4(),
        cliente_app_user_id=user_id,
        recompensa_slug="desc5",
        recompensa_label="5% off na próxima fatura",
        pontos_gastos=500,
        status="pendente",
        obs_admin=None,
        criado_em=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_admin_resgate_out_inclui_dados_do_cliente() -> None:
    user = ClienteAppUser(
        id=uuid4(),
        cpf_hash="h",
        cpf_last4="1234",
        cpf_encrypted=encrypt_pii("12345678901"),
        nome_encrypted=encrypt_pii("Maria Souza"),
        telefone_encrypted=encrypt_pii("5592999998888"),
    )
    out = _admin_resgate_out(_resgate(user.id), user)
    assert out.cliente_nome == "Maria Souza"
    assert out.cliente_cpf_last4 == "1234"
    assert out.cliente_telefone == "5592999998888"
    assert out.cliente_app_user_id == str(user.id)


def test_admin_resgate_out_sem_user_nao_quebra() -> None:
    out = _admin_resgate_out(_resgate(uuid4()), None)
    assert out.cliente_nome == ""
    assert out.cliente_cpf_last4 == ""
    assert out.cliente_telefone is None
