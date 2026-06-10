"""Resolucao do plano de troca de senha (puro, sem rede)."""
from __future__ import annotations

from ondeline_api.adapters.genieacs.base import GenieAcsDevice, RedeWlan
from ondeline_api.adapters.genieacs.wifi_paths import montar_plano, perfil_do_modelo

_BASE = "InternetGatewayDevice.LANDevice.1.WLANConfiguration"


def _device(modelo: str, redes: list[RedeWlan]) -> GenieAcsDevice:
    return GenieAcsDevice(device_id="d1", modelo=modelo, redes=redes)


def test_seta_senha_so_nas_redes_ativas() -> None:
    dev = _device(
        "AX1800",
        [
            RedeWlan(instancia=1, ssid="CASA_5G", enabled=True),
            RedeWlan(instancia=6, ssid="CASA", enabled=True),
            RedeWlan(instancia=2, ssid="DESATIVADA", enabled=False),
        ],
    )
    plano = montar_plano(dev, "NovaSenha123")
    paths = [p[0] for p in plano.params]
    assert f"{_BASE}.1.KeyPassphrase" in paths
    assert f"{_BASE}.6.KeyPassphrase" in paths
    assert f"{_BASE}.2.KeyPassphrase" not in paths
    assert all(p[1] == "NovaSenha123" and p[2] == "xsd:string" for p in plano.params)


def test_ax1800_precisa_reboot() -> None:
    dev = _device("AX1800", [RedeWlan(instancia=1, ssid="x", enabled=True)])
    assert montar_plano(dev, "s").needs_reboot is True


def test_modelo_desconhecido_usa_default_conservador() -> None:
    perfil = perfil_do_modelo("MODELO_QUE_NAO_EXISTE")
    assert perfil.needs_reboot is True
    assert perfil.passphrase_param == "KeyPassphrase"


def test_fiberhome_enabled_false_usa_ssid_custom() -> None:
    # HG6145D reporta Enable=false ate nas redes no ar -> cai pras de SSID
    # customizado (GABRIEL), pulando os defaults de fabrica (fh_ssid*).
    dev = _device(
        "HG6145D",
        [
            RedeWlan(instancia=1, ssid="GABRIEL", enabled=False),
            RedeWlan(instancia=5, ssid="GABRIEL", enabled=False),
            RedeWlan(instancia=2, ssid="fh_ssid2", enabled=False),
            RedeWlan(instancia=3, ssid="fh_5G_ssid3", enabled=False),
        ],
    )
    paths = [p[0] for p in montar_plano(dev, "s").params]
    assert any(".1.KeyPassphrase" in p for p in paths)
    assert any(".5.KeyPassphrase" in p for p in paths)
    assert not any(".2.KeyPassphrase" in p for p in paths)  # fh_ default pulado
    assert not any(".3.KeyPassphrase" in p for p in paths)


def test_enabled_true_tem_prioridade_sobre_fallback() -> None:
    # Quando ha rede Enable=true, usa so ela (nao cai no fallback de SSID).
    dev = _device(
        "AX1800",
        [
            RedeWlan(instancia=1, ssid="CASA", enabled=True),
            RedeWlan(instancia=2, ssid="EXTRA", enabled=False),
        ],
    )
    paths = [p[0] for p in montar_plano(dev, "s").params]
    assert paths == ["InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.KeyPassphrase"]


def test_so_ssid_default_plano_vazio() -> None:
    # Device so com SSID default de fabrica (nenhuma rede do cliente) -> vazio.
    dev = _device("HG6145D", [RedeWlan(instancia=2, ssid="fh_ssid2", enabled=False)])
    assert montar_plano(dev, "s").params == []
