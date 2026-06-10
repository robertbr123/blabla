"""Mapa modelo -> perfil WiFi e montagem do plano de troca de senha.

Achados do spike (memoria rede_wifi_genieacs): a senha mora em
`...WLANConfiguration.{i}.KeyPassphrase`; e write-only (GET volta vazio).
O 5G so aplica apos reboot. Setamos a senha em TODAS as instancias ativas
(Enable=true) com o mesmo valor - cobre 2.4 e 5G sem classificar banda.

Mapa extensivel por modelo. Default conservador (reinicia sempre) ate o
modelo ser mapeado.
"""
from __future__ import annotations

from dataclasses import dataclass

from ondeline_api.adapters.genieacs.base import GenieAcsDevice

WLAN_BASE = "InternetGatewayDevice.LANDevice.1.WLANConfiguration"


@dataclass(frozen=True, slots=True)
class WifiPerfil:
    passphrase_param: str
    needs_reboot: bool


@dataclass(frozen=True, slots=True)
class PlanoTrocaSenha:
    params: list[tuple[str, str, str]]  # (path, valor, xsd type)
    needs_reboot: bool


# Confirmado no spike: AX1800 (Intelbras) usa KeyPassphrase e exige reboot
# pro 5G aplicar. Novos modelos: adicionar aqui (ex.: PreSharedKey.1.KeyPassphrase).
PERFIS: dict[str, WifiPerfil] = {
    "AX1800": WifiPerfil(passphrase_param="KeyPassphrase", needs_reboot=True),
}

# Modelo desconhecido: caminho mais comum (TR-098) + reboot por seguranca.
DEFAULT_PERFIL = WifiPerfil(passphrase_param="KeyPassphrase", needs_reboot=True)


def perfil_do_modelo(modelo: str) -> WifiPerfil:
    return PERFIS.get(modelo, DEFAULT_PERFIL)


# Prefixos de SSID default de fabrica (rede nunca configurada pelo cliente).
_SSID_DEFAULT_PREFIXOS = ("fh_", "fh-")


def _e_ssid_default(ssid: str) -> bool:
    s = ssid.lower()
    return any(s.startswith(p) for p in _SSID_DEFAULT_PREFIXOS)


def _redes_alvo(device: GenieAcsDevice) -> list[int]:
    """Instancias onde setar a senha. Preferimos as Enable=true; mas alguns
    modelos (FiberHome HG6145D) reportam Enable=false ate nas redes que estao
    no ar, entao caimos pras redes com SSID customizado (pulando defaults
    de fabrica fh_*)."""
    ativas = [r.instancia for r in device.redes if r.enabled and r.ssid]
    if ativas:
        return ativas
    return [
        r.instancia
        for r in device.redes
        if r.ssid and not _e_ssid_default(r.ssid)
    ]


def montar_plano(device: GenieAcsDevice, nova_senha: str) -> PlanoTrocaSenha:
    perfil = perfil_do_modelo(device.modelo)
    params = [
        (f"{WLAN_BASE}.{inst}.{perfil.passphrase_param}", nova_senha, "xsd:string")
        for inst in _redes_alvo(device)
    ]
    return PlanoTrocaSenha(params=params, needs_reboot=perfil.needs_reboot)
