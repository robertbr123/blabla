"""RedeService - orquestra a troca de senha WiFi via GenieACS.

Resolve a ONU a partir do cliente local: Cliente.cpf -> SGP -> contrato ->
pppoe_login -> device no GenieACS (fallback serial). Valida a senha (WPA),
envia Set(senha nas redes ativas)+Reboot, registra o pedido. Otimista:
a senha e write-only, nao da pra confirmar por read-back.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.genieacs.base import GenieAcsDevice
from ondeline_api.adapters.genieacs.wifi_paths import montar_plano
from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.models.rede import RedeWifiPedido

log = structlog.get_logger(__name__)

SENHA_MIN = 8
SENHA_MAX = 63


class SenhaInvalidaError(ValueError):
    """Senha fora do range WPA-PSK (8-63 chars ASCII)."""


class OnuNaoEncontradaError(Exception):
    """Nao foi possivel resolver a ONU (sem PPPoE no GenieACS e sem serial)."""


class _GenieProto(Protocol):
    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None: ...
    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None: ...
    async def set_parameter_values(
        self, device_id: str, params: list[tuple[str, str, str]]
    ) -> None: ...
    async def reboot(self, device_id: str) -> None: ...


class _SgpCacheProto(Protocol):
    async def get_cliente(self, cpf: str) -> ClienteSgp | None: ...


@dataclass(frozen=True, slots=True)
class StatusRede:
    encontrada: bool
    device: GenieAcsDevice | None = None
    pppoe_login: str | None = None
    motivo: str | None = None  # "onu_nao_encontrada" quando encontrada=False


@dataclass(frozen=True, slots=True)
class ResultadoTroca:
    device_id: str
    reiniciando: bool


def _primeiro_contrato(contratos: list[Contrato]) -> Contrato | None:
    for c in contratos:
        if c.status and "ativ" in c.status.lower():
            return c
    return contratos[0] if contratos else None


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
        genieacs: _GenieProto,
        sgp_cache: _SgpCacheProto,
    ) -> None:
        self._session = session
        self._genie = genieacs
        self._sgp = sgp_cache

    async def _contrato_do_cliente(self, cliente_id: UUID) -> Contrato | None:
        cliente = (
            await self._session.execute(select(Cliente).where(Cliente.id == cliente_id))
        ).scalar_one_or_none()
        if cliente is None:
            return None
        cpf = decrypt_pii(cliente.cpf_cnpj_encrypted)
        cli_sgp = await self._sgp.get_cliente(cpf)
        if cli_sgp is None:
            return None
        return _primeiro_contrato(cli_sgp.contratos)

    async def _resolver_device(
        self, cliente_id: UUID, serial: str | None
    ) -> tuple[GenieAcsDevice | None, Contrato | None]:
        """Retorna (device, contrato). Resolve o contrato UMA vez e devolve
        junto pra quem precisar do id/pppoe sem reconsultar. Tenta achar a ONU
        pelo PPPoE do contrato; cai pro serial."""
        contrato = await self._contrato_do_cliente(cliente_id)
        pppoe = contrato.pppoe_login if contrato and contrato.pppoe_login else None
        device: GenieAcsDevice | None = None
        if pppoe:
            device = await self._genie.find_device_by_pppoe(pppoe)
        if device is None and serial:
            device = await self._genie.find_device_by_serial(serial)
        return device, contrato

    async def status_rede(self, cliente_id: UUID, serial: str | None = None) -> StatusRede:
        device, contrato = await self._resolver_device(cliente_id, serial)
        pppoe = contrato.pppoe_login if contrato and contrato.pppoe_login else None
        if device is None:
            return StatusRede(
                encontrada=False, pppoe_login=pppoe, motivo="onu_nao_encontrada"
            )
        return StatusRede(encontrada=True, device=device, pppoe_login=pppoe)

    async def trocar_senha_wifi(
        self,
        *,
        cliente_id: UUID,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
    ) -> ResultadoTroca:
        _validar_senha(nova_senha)
        device, contrato = await self._resolver_device(cliente_id, serial)
        if device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")

        plano = montar_plano(device, nova_senha)
        pppoe = contrato.pppoe_login if contrato and contrato.pppoe_login else None

        # Registra ANTES do envio (status=pendente) e da flush: auditoria de
        # troca de senha nao pode perder uma troca que JA aplicou na ONU. Se o
        # envio falhar (GenieAcsUnavailableError), o registro sobrevive como
        # 'pendente' e o erro propaga. So depois do envio OK vira 'enviado'.
        pedido = RedeWifiPedido(
            cliente_id=cliente_id,
            contrato_id=contrato.id if contrato else None,
            pppoe_login=pppoe,
            device_id=device.device_id,
            ator_user_id=ator_user_id,
            status="pendente",
            reiniciou=plano.needs_reboot,
        )
        self._session.add(pedido)
        await self._session.flush()

        if plano.params:
            await self._genie.set_parameter_values(device.device_id, plano.params)
        if plano.needs_reboot:
            await self._genie.reboot(device.device_id)

        pedido.status = "enviado"
        await self._session.flush()
        log.info(
            "rede.senha_trocada",
            cliente_id=str(cliente_id),
            device_id=device.device_id,
            redes=len(plano.params),
            reboot=plano.needs_reboot,
        )
        return ResultadoTroca(device_id=device.device_id, reiniciando=plano.needs_reboot)
