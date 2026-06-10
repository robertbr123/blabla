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


def test_sem_rede_ativa_plano_vazio() -> None:
    dev = _device("AX1800", [RedeWlan(instancia=1, ssid="x", enabled=False)])
    assert montar_plano(dev, "s").params == []
