"""RedeService - orquestra a troca de senha WiFi via GenieACS.

Resolucao da ONU = CPF -> SGP -> contrato -> pppoe_login -> device no GenieACS,
com fallback no serial. O SGP e a FONTE de verdade do PPPoE: ele faz o RADIUS,
entao o `login` do contrato no SGP E, por construcao, o mesmo
`WANPPPConnection.Username` que esta na ONU. Funciona para TODOS os clientes
(inclusive os antigos que so existem no SGP, sem cadastro local) e e a mesma
resolucao que o app do cliente vai usar (CPF do proprio login).

Senha write-only -> confirmacao otimista (sem read-back).

Obs: pra o PPPoE resolver, o GenieACS precisa ter lido o WANPPPConnection.Username
do device (preset/refresh). Enquanto isso nao estiver provisionado, o serial
fallback cobre (o tecnico tem o serial na instalacao).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsDevice
from ondeline_api.adapters.genieacs.wifi_paths import montar_plano
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato
from ondeline_api.db.crypto import hash_pii
from ondeline_api.db.models.rede import RedeWifiPedido

log = structlog.get_logger(__name__)

SENHA_MIN = 8
SENHA_MAX = 63


def qualidade_sinal(rx_power: float | None) -> tuple[str, str]:
    """(label, emoji) do RX power GPON (dBm). Mesmas faixas da Fatia 2/3:
    verde -8..-25, amarelo -25..-27, vermelho fora; cinza se desconhecido."""
    if rx_power is None:
        return ("desconhecido", "⚪")
    if rx_power > -8 or rx_power < -27:
        return ("critico", "🔴")
    if rx_power < -25:
        return ("atencao", "🟡")
    return ("bom", "🟢")


class GenieProto(Protocol):
    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None: ...
    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None: ...
    async def set_parameter_values(
        self, device_id: str, params: list[tuple[str, str, str]]
    ) -> None: ...
    async def reboot(self, device_id: str) -> None: ...
    async def refresh_wan(self, device_id: str) -> None: ...


class SgpCacheProto(Protocol):
    async def get_cliente(self, cpf: str) -> ClienteSgp | None: ...


class SenhaInvalidaError(ValueError):
    """Senha fora do range WPA-PSK (8-63 chars ASCII imprimivel)."""


class CpfInvalidoError(ValueError):
    """CPF/CNPJ sem digitos suficientes."""


class OnuNaoEncontradaError(Exception):
    """Nao foi possivel resolver a ONU (sem PPPoE no GenieACS e sem serial)."""


@dataclass(frozen=True, slots=True)
class StatusRede:
    encontrada: bool
    device: GenieAcsDevice | None = None
    pppoe_login: str | None = None
    motivo: str | None = None  # "onu_nao_encontrada" quando encontrada=False


@dataclass(frozen=True, slots=True)
class DiagnosticoRede:
    encontrada: bool
    device: GenieAcsDevice | None = None
    pppoe_login: str | None = None
    motivo: str | None = None  # "onu_nao_encontrada" quando encontrada=False


@dataclass(frozen=True, slots=True)
class ResultadoTroca:
    device_id: str
    reiniciando: bool


@dataclass(frozen=True, slots=True)
class ResultadoReboot:
    device_id: str


@dataclass(frozen=True, slots=True)
class _Resolucao:
    device: GenieAcsDevice | None
    pppoe: str | None
    contrato_id: str | None


def _contratos_ordenados(contratos: list[Contrato]) -> list[Contrato]:
    """Contratos com pppoe primeiro (so esses resolvem ONU), ativos antes."""
    com_pppoe = [c for c in contratos if c.pppoe_login]
    ativos = [c for c in com_pppoe if c.status and "ativ" in c.status.lower()]
    inativos = [c for c in com_pppoe if c not in ativos]
    return ativos + inativos


def _so_digitos(cpf: str) -> str:
    return "".join(ch for ch in (cpf or "") if ch.isdigit())


def _validar_senha(senha: str) -> None:
    if not (SENHA_MIN <= len(senha) <= SENHA_MAX):
        raise SenhaInvalidaError("senha WiFi deve ter 8 a 63 caracteres")
    # So ASCII imprimivel (0x20 espaco ate 0x7e ~). Rejeita controle (\n, \t,
    # \x00): senha write-only, nao da pra ler de volta pra notar o erro, e o
    # cliente ficaria sem conseguir conectar.
    if not all(0x20 <= ord(c) <= 0x7E for c in senha):
        raise SenhaInvalidaError("senha WiFi so aceita caracteres ASCII imprimiveis")


class RedeService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        genieacs: GenieProto,
        sgp_cache: SgpCacheProto,
    ) -> None:
        self._session = session
        self._genie = genieacs
        self._sgp = sgp_cache

    async def _resolver_por_cpf(self, cpf: str, serial: str | None) -> _Resolucao:
        """CPF -> SGP -> contrato -> pppoe -> device. PPPoE e a chave PRINCIPAL
        (o SGP faz o RADIUS, entao o login bate com o Username na ONU); serial
        e o fallback. Reusado pelo app do cliente (passa o CPF do login).

        Cliente pode ter VARIOS contratos (varias ONUs): tenta CADA pppoe e usa
        o primeiro que tem ONU registrada no GenieACS."""
        cli = await self._sgp.get_cliente(cpf)
        contratos = _contratos_ordenados(cli.contratos) if cli else []

        for contrato in contratos:
            pppoe = contrato.pppoe_login
            device = await self._genie.find_device_by_pppoe(pppoe)
            if device is not None:
                return _Resolucao(device=device, pppoe=pppoe, contrato_id=contrato.id or None)

        # Nenhum contrato resolveu pelo pppoe -> fallback serial. Guarda o pppoe
        # do 1o contrato como referencia de auditoria.
        ref = contratos[0] if contratos else None
        pppoe_ref = ref.pppoe_login if ref else None
        contrato_ref = (ref.id or None) if ref else None
        device = (
            await self._genie.find_device_by_serial(serial) if serial else None
        )
        return _Resolucao(device=device, pppoe=pppoe_ref, contrato_id=contrato_ref)

    async def status_rede(self, cpf: str, serial: str | None = None) -> StatusRede:
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            return StatusRede(
                encontrada=False, pppoe_login=res.pppoe, motivo="onu_nao_encontrada"
            )
        return StatusRede(encontrada=True, device=res.device, pppoe_login=res.pppoe)

    async def diagnostico_rede(
        self, cpf: str, serial: str | None = None
    ) -> DiagnosticoRede:
        """Read-only: aparelhos conectados + sinal da fibra. Dispara um
        refreshObject best-effort do WANDevice (popula optico/PPPoE no proximo
        inform) e retorna o que ja esta na arvore do device."""
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            return DiagnosticoRede(
                encontrada=False, pppoe_login=res.pppoe, motivo="onu_nao_encontrada"
            )
        await self._genie.refresh_wan(res.device.device_id)  # best-effort no client
        return DiagnosticoRede(encontrada=True, device=res.device, pppoe_login=res.pppoe)

    async def trocar_senha_wifi(
        self,
        *,
        cpf: str,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
    ) -> ResultadoTroca:
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        _validar_senha(nova_senha)
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")

        plano = montar_plano(res.device, nova_senha)

        # Registra ANTES do envio (status=pendente) e da flush: auditoria de
        # troca de senha nao pode perder uma troca que JA aplicou na ONU. Se o
        # envio falhar (GenieAcsUnavailableError), o registro sobrevive como
        # 'pendente' e o erro propaga. So depois do envio OK vira 'enviado'.
        pedido = RedeWifiPedido(
            cpf_hash=hash_pii(cpf),
            contrato_id=res.contrato_id,
            pppoe_login=res.pppoe,
            device_id=res.device.device_id,
            ator_user_id=ator_user_id,
            status="pendente",
            reiniciou=plano.needs_reboot,
        )
        self._session.add(pedido)
        await self._session.flush()

        if plano.params:
            await self._genie.set_parameter_values(res.device.device_id, plano.params)
        if plano.needs_reboot:
            await self._genie.reboot(res.device.device_id)

        pedido.status = "enviado"
        await self._session.flush()
        log.info(
            "rede.senha_trocada",
            device_id=res.device.device_id,
            redes=len(plano.params),
            reboot=plano.needs_reboot,
        )
        return ResultadoTroca(
            device_id=res.device.device_id, reiniciando=plano.needs_reboot
        )

    async def reiniciar_onu(
        self, *, cpf: str, serial: str | None, ator_user_id: UUID
    ) -> ResultadoReboot:
        """Reinicia a ONU (acao de suporte). Audita em rede_wifi_pedido com
        tipo='reboot' (mesma tabela da troca de senha, PII-safe)."""
        cpf = _so_digitos(cpf)
        if not cpf:
            raise CpfInvalidoError("CPF invalido")
        res = await self._resolver_por_cpf(cpf, serial)
        if res.device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")
        pedido = RedeWifiPedido(
            cpf_hash=hash_pii(cpf),
            contrato_id=res.contrato_id,
            pppoe_login=res.pppoe,
            device_id=res.device.device_id,
            ator_user_id=ator_user_id,
            status="pendente",
            reiniciou=True,
            tipo="reboot",
        )
        self._session.add(pedido)
        await self._session.flush()
        await self._genie.reboot(res.device.device_id)
        pedido.status = "enviado"
        await self._session.flush()
        log.info("rede.onu_reiniciada", device_id=res.device.device_id)
        return ResultadoReboot(device_id=res.device.device_id)
