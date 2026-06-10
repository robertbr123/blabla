"""RedeService: resolve ONU (CPF->SGP->pppoe, fallback serial), troca, registra."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato, SgpProviderEnum
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import ClienteCadastro
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.services.rede_service import (
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class _FakeGenie:
    def __init__(self, *, by_pppoe: GenieAcsDevice | None = None,
                 by_serial: GenieAcsDevice | None = None) -> None:
        self._by_pppoe = by_pppoe
        self._by_serial = by_serial
        self.set_calls: list[tuple[str, list[tuple[str, str, str]]]] = []
        self.reboots: list[str] = []

    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
        return self._by_pppoe

    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None:
        return self._by_serial

    async def set_parameter_values(self, device_id, params):
        self.set_calls.append((device_id, params))

    async def reboot(self, device_id):
        self.reboots.append(device_id)


class _FakeSgpCache:
    def __init__(self, cliente: ClienteSgp | None) -> None:
        self._cliente = cliente

    async def get_cliente(self, cpf: str) -> ClienteSgp | None:
        return self._cliente


def _dev() -> GenieAcsDevice:
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        online=True,
        redes=[RedeWlan(instancia=1, ssid="CASA_5G", enabled=True),
               RedeWlan(instancia=6, ssid="CASA", enabled=True)],
    )


def _cli_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="42", nome="Maria", cpf_cnpj="11122233344",
        contratos=[Contrato(id="C1", plano="100MB", status="ativo", pppoe_login="ppp5")],
    )


async def _make_cadastro(
    db_session: AsyncSession, *, serial: str | None = None
) -> ClienteCadastro:
    cpf = uuid4().hex[:11]
    cad = ClienteCadastro(
        cpf_hash=hash_pii(cpf), cpf_encrypted=encrypt_pii(cpf),
        nome_encrypted=encrypt_pii("Maria"), dob=date(1990, 1, 1),
        telefone_encrypted=encrypt_pii("5592999"), address="Rua X", number="10",
        city="Manaus", plan_nome="100MB", installer_nome="Tec", due_date=10,
        serial=serial,
    )
    db_session.add(cad)
    await db_session.flush()
    return cad


async def test_troca_seta_as_redes_e_reinicia_e_registra(db_session: AsyncSession) -> None:
    cad = await _make_cadastro(db_session)
    genie = _FakeGenie(by_pppoe=_dev())
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    ator = uuid4()

    res = await svc.trocar_senha_wifi(
        cadastro_id=cad.id, nova_senha="NovaSenha123", serial=None, ator_user_id=ator
    )

    assert res.device_id == "30E1F1-AX1800-X"
    assert res.reiniciando is True
    assert len(genie.set_calls) == 1
    paths = [p[0] for p in genie.set_calls[0][1]]
    assert any(".1.KeyPassphrase" in p for p in paths)
    assert any(".6.KeyPassphrase" in p for p in paths)
    assert genie.reboots == ["30E1F1-AX1800-X"]
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.device_id == "30E1F1-AX1800-X"
    assert pedido.ator_user_id == ator
    assert pedido.pppoe_login == "ppp5"  # veio do SGP (fonte)
    assert pedido.status == "enviado"


async def test_senha_curta_rejeitada(db_session: AsyncSession) -> None:
    cad = await _make_cadastro(db_session)
    svc = RedeService(session=db_session, genieacs=_FakeGenie(by_pppoe=_dev()),
                      sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(SenhaInvalidaError):
        await svc.trocar_senha_wifi(cadastro_id=cad.id, nova_senha="curta", serial=None,
                                    ator_user_id=uuid4())


async def test_fallback_serial_quando_pppoe_nao_acha(db_session: AsyncSession) -> None:
    cad = await _make_cadastro(db_session)
    genie = _FakeGenie(by_pppoe=None, by_serial=_dev())
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    res = await svc.trocar_senha_wifi(cadastro_id=cad.id, nova_senha="NovaSenha123",
                                      serial="ITBSF1", ator_user_id=uuid4())
    assert res.device_id == "30E1F1-AX1800-X"


async def test_sem_pppoe_e_sem_serial_levanta(db_session: AsyncSession) -> None:
    cad = await _make_cadastro(db_session)
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(OnuNaoEncontradaError):
        await svc.trocar_senha_wifi(cadastro_id=cad.id, nova_senha="NovaSenha123",
                                    serial=None, ator_user_id=uuid4())


async def test_senha_com_caractere_de_controle_rejeitada(db_session: AsyncSession) -> None:
    cad = await _make_cadastro(db_session)
    svc = RedeService(session=db_session, genieacs=_FakeGenie(by_pppoe=_dev()),
                      sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(SenhaInvalidaError):
        await svc.trocar_senha_wifi(cadastro_id=cad.id, nova_senha="Senha\n123", serial=None,
                                    ator_user_id=uuid4())


async def test_falha_no_envio_deixa_pedido_pendente(db_session: AsyncSession) -> None:
    from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError

    class _GenieQuebra(_FakeGenie):
        async def set_parameter_values(self, device_id, params):
            raise GenieAcsUnavailableError("nbi fora")

    cad = await _make_cadastro(db_session)
    svc = RedeService(session=db_session, genieacs=_GenieQuebra(by_pppoe=_dev()),
                      sgp_cache=_FakeSgpCache(_cli_sgp()))
    with pytest.raises(GenieAcsUnavailableError):
        await svc.trocar_senha_wifi(cadastro_id=cad.id, nova_senha="NovaSenha123",
                                    serial=None, ator_user_id=uuid4())
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.status == "pendente"


async def test_resolver_por_cpf_sem_cadastro(db_session: AsyncSession) -> None:
    """Core reusavel pelo futuro app cliente: cliente que SO existe no SGP
    (nenhum cadastro de campo) resolve a ONU pelo CPF -> SGP -> pppoe."""
    genie = _FakeGenie(by_pppoe=_dev())
    svc = RedeService(session=db_session, genieacs=genie, sgp_cache=_FakeSgpCache(_cli_sgp()))
    res = await svc._resolver_por_cpf("11122233344", None)
    assert res.device is not None
    assert res.device.device_id == "30E1F1-AX1800-X"
    assert res.pppoe == "ppp5"
    assert res.contrato_id == "C1"
