"""RedeService: resolve ONU (CPF->SGP->pppoe, fallback serial), troca, registra."""
from __future__ import annotations

from uuid import uuid4

import pytest
from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato, SgpProviderEnum
from ondeline_api.db.crypto import hash_pii
from ondeline_api.db.models.rede import RedeWifiPedido
from ondeline_api.services.rede_service import (
    CpfInvalidoError,
    OnuNaoEncontradaError,
    RedeService,
    SenhaInvalidaError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

CPF = "04099889289"


class _FakeGenie:
    def __init__(self, *, by_pppoe: GenieAcsDevice | None = None,
                 by_serial: GenieAcsDevice | None = None) -> None:
        self._by_pppoe = by_pppoe
        self._by_serial = by_serial
        self.set_calls: list[tuple[str, list[tuple[str, str, str]]]] = []
        self.reboots: list[str] = []
        self.refresh_calls: list[str] = []

    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
        return self._by_pppoe

    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None:
        return self._by_serial

    async def set_parameter_values(self, device_id, params):
        self.set_calls.append((device_id, params))

    async def reboot(self, device_id):
        self.reboots.append(device_id)

    async def refresh_wan(self, device_id):
        self.refresh_calls.append(device_id)


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
        provider=SgpProviderEnum.ONDELINE, sgp_id="42", nome="Rosineide", cpf_cnpj=CPF,
        contratos=[Contrato(id="C1", plano="100MB", status="ativo",
                            pppoe_login="rosineidesilva")],
    )


def _svc(db_session: AsyncSession, genie: _FakeGenie,
         cli: ClienteSgp | None = None) -> RedeService:
    return RedeService(session=db_session, genieacs=genie,
                       sgp_cache=_FakeSgpCache(cli if cli is not None else _cli_sgp()))


async def test_troca_seta_as_redes_e_reinicia_e_registra(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev())
    svc = _svc(db_session, genie)
    ator = uuid4()

    res = await svc.trocar_senha_wifi(
        cpf=CPF, nova_senha="NovaSenha123", serial=None, ator_user_id=ator
    )

    assert res.device_id == "30E1F1-AX1800-X"
    assert res.reiniciando is True
    paths = [p[0] for p in genie.set_calls[0][1]]
    assert any(".1.KeyPassphrase" in p for p in paths)
    assert any(".6.KeyPassphrase" in p for p in paths)
    assert genie.reboots == ["30E1F1-AX1800-X"]
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.device_id == "30E1F1-AX1800-X"
    assert pedido.ator_user_id == ator
    assert pedido.cpf_hash == hash_pii(CPF)  # PII-safe, sem CPF em claro
    assert pedido.pppoe_login == "rosineidesilva"  # veio do SGP (RADIUS)
    assert pedido.status == "enviado"


async def test_cpf_aceita_com_pontuacao(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev())
    svc = _svc(db_session, genie)
    res = await svc.trocar_senha_wifi(
        cpf="040.998.892-89", nova_senha="NovaSenha123", serial=None, ator_user_id=uuid4()
    )
    assert res.device_id == "30E1F1-AX1800-X"


async def test_cpf_vazio_rejeitado(db_session: AsyncSession) -> None:
    svc = _svc(db_session, _FakeGenie(by_pppoe=_dev()))
    with pytest.raises(CpfInvalidoError):
        await svc.trocar_senha_wifi(cpf="---", nova_senha="NovaSenha123", serial=None,
                                    ator_user_id=uuid4())


async def test_senha_curta_rejeitada(db_session: AsyncSession) -> None:
    svc = _svc(db_session, _FakeGenie(by_pppoe=_dev()))
    with pytest.raises(SenhaInvalidaError):
        await svc.trocar_senha_wifi(cpf=CPF, nova_senha="curta", serial=None,
                                    ator_user_id=uuid4())


async def test_fallback_serial_quando_pppoe_nao_acha(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=_dev())
    svc = _svc(db_session, genie)
    res = await svc.trocar_senha_wifi(cpf=CPF, nova_senha="NovaSenha123",
                                      serial="ITBSF1", ator_user_id=uuid4())
    assert res.device_id == "30E1F1-AX1800-X"


async def test_sem_pppoe_e_sem_serial_levanta(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = _svc(db_session, genie)
    with pytest.raises(OnuNaoEncontradaError):
        await svc.trocar_senha_wifi(cpf=CPF, nova_senha="NovaSenha123",
                                    serial=None, ator_user_id=uuid4())


async def test_cliente_so_no_sgp_resolve_por_pppoe(db_session: AsyncSession) -> None:
    """Cliente antigo (so no SGP, sem cadastro local): CPF -> SGP -> pppoe -> ONU."""
    genie = _FakeGenie(by_pppoe=_dev())
    svc = _svc(db_session, genie)
    st = await svc.status_rede(CPF)
    assert st.encontrada is True
    assert st.pppoe_login == "rosineidesilva"


async def test_multi_contrato_usa_o_que_tem_onu(db_session: AsyncSession) -> None:
    """Cliente com 2 contratos: o 1o pppoe nao tem ONU no GenieACS, o 2o tem.
    Deve achar pelo 2o (nao parar no 1o como antes)."""
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE, sgp_id="7", nome="Multi", cpf_cnpj=CPF,
        contratos=[
            Contrato(id="A", plano="X", status="ativo", pppoe_login="ppp_sem_onu"),
            Contrato(id="B", plano="Y", status="ativo", pppoe_login="ppp6"),
        ],
    )

    class _GenieMulti(_FakeGenie):
        async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None:
            return _dev() if login == "ppp6" else None

    svc = RedeService(session=db_session, genieacs=_GenieMulti(),
                      sgp_cache=_FakeSgpCache(cli))
    res = await svc.trocar_senha_wifi(cpf=CPF, nova_senha="NovaSenha123",
                                      serial=None, ator_user_id=uuid4())
    assert res.device_id == "30E1F1-AX1800-X"
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.contrato_id == "B"  # o contrato que tinha ONU
    assert pedido.pppoe_login == "ppp6"


async def test_senha_com_caractere_de_controle_rejeitada(db_session: AsyncSession) -> None:
    svc = _svc(db_session, _FakeGenie(by_pppoe=_dev()))
    with pytest.raises(SenhaInvalidaError):
        await svc.trocar_senha_wifi(cpf=CPF, nova_senha="Senha\n123", serial=None,
                                    ator_user_id=uuid4())


async def test_falha_no_envio_deixa_pedido_pendente(db_session: AsyncSession) -> None:
    from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError

    class _GenieQuebra(_FakeGenie):
        async def set_parameter_values(self, device_id, params):
            raise GenieAcsUnavailableError("nbi fora")

    svc = _svc(db_session, _GenieQuebra(by_pppoe=_dev()))
    with pytest.raises(GenieAcsUnavailableError):
        await svc.trocar_senha_wifi(cpf=CPF, nova_senha="NovaSenha123",
                                    serial=None, ator_user_id=uuid4())
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.status == "pendente"


def _dev_diag() -> GenieAcsDevice:
    from ondeline_api.adapters.genieacs.base import Aparelho, SinalFibra
    return GenieAcsDevice(
        device_id="30E1F1-AX1800-X",
        modelo="AX1800",
        online=True,
        aparelhos=[Aparelho(nome="Cel", ip="192.168.1.2", mac="AA:01", ativo=True)],
        sinal=SinalFibra(rx_power=-26.5, conexao_pppoe="Connected"),
    )


async def test_diagnostico_resolve_dispara_refresh_e_retorna(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev_diag())
    svc = _svc(db_session, genie)
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is True
    assert diag.device is not None
    assert diag.device.aparelhos[0].mac == "AA:01"
    assert diag.device.sinal is not None and diag.device.sinal.rx_power == -26.5
    assert genie.refresh_calls == ["30E1F1-AX1800-X"]  # refresh disparado


async def test_diagnostico_onu_nao_encontrada(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = _svc(db_session, genie)
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is False
    assert diag.motivo == "onu_nao_encontrada"
    assert genie.refresh_calls == []  # sem device, sem refresh


async def test_diagnostico_cpf_vazio_rejeitado(db_session: AsyncSession) -> None:
    svc = _svc(db_session, _FakeGenie(by_pppoe=_dev_diag()))
    with pytest.raises(CpfInvalidoError):
        await svc.diagnostico_rede("---")


async def test_reiniciar_onu_reboota_e_audita(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev())
    svc = _svc(db_session, genie)
    ator = uuid4()
    res = await svc.reiniciar_onu(cpf=CPF, serial=None, ator_user_id=ator)
    assert res.device_id == "30E1F1-AX1800-X"
    assert genie.reboots == ["30E1F1-AX1800-X"]
    pedido = (await db_session.execute(select(RedeWifiPedido))).scalar_one()
    assert pedido.tipo == "reboot"
    assert pedido.reiniciou is True
    assert pedido.status == "enviado"
    assert pedido.ator_user_id == ator
    assert pedido.cpf_hash == hash_pii(CPF)


async def test_reiniciar_onu_sem_device_levanta(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=None, by_serial=None)
    svc = _svc(db_session, genie)
    with pytest.raises(OnuNaoEncontradaError):
        await svc.reiniciar_onu(cpf=CPF, serial=None, ator_user_id=uuid4())


async def test_diagnostico_inclui_pppoe(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev_diag())
    svc = _svc(db_session, genie)
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is True
    assert diag.pppoe_login == "rosineidesilva"


async def test_snapshot_sinal_ok_e_best_effort(db_session: AsyncSession) -> None:
    from ondeline_api.adapters.genieacs.base import (
        GenieAcsDevice,
        GenieAcsUnavailableError,
        SinalFibra,
    )
    from ondeline_api.services.rede_service import DiagnosticoRede, snapshot_sinal

    class _OkRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            dev = GenieAcsDevice(
                device_id="X",
                sinal=SinalFibra(rx_power=-26.0, tx_power=2.0, status_gpon="Up"),
            )
            return DiagnosticoRede(encontrada=True, device=dev)

    snap = await snapshot_sinal(_OkRede(), "04099889289")
    assert snap is not None
    assert snap["rx_power"] == -26.0
    assert snap["qualidade"] == "atencao"

    class _DownRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            raise GenieAcsUnavailableError("fora")

    assert await snapshot_sinal(_DownRede(), "04099889289") is None

    class _SemOnu:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            return DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada")

    assert await snapshot_sinal(_SemOnu(), "04099889289") is None


def test_qualidade_sinal_faixas() -> None:
    from ondeline_api.services.rede_service import qualidade_sinal
    assert qualidade_sinal(None) == ("desconhecido", "⚪")
    assert qualidade_sinal(-13.0) == ("bom", "🟢")
    assert qualidade_sinal(-25.0) == ("bom", "🟢")      # -25 inclusive = bom
    assert qualidade_sinal(-26.0) == ("atencao", "🟡")
    assert qualidade_sinal(-28.0) == ("critico", "🔴")  # < -27
    assert qualidade_sinal(-5.0) == ("critico", "🔴")   # > -8 quente demais
