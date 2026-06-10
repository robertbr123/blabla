"""RedeService - orquestra a troca de senha WiFi via GenieACS.

Resolucao da ONU = CPF -> SGP -> contrato -> pppoe_login -> device no GenieACS,
com fallback no serial. O SGP e a FONTE de verdade do PPPoE (todos os clientes
estao la, inclusive os antigos que nenhum tecnico cadastrou). O metodo core
`_resolver_por_cpf` e reusavel: hoje o app do tecnico chega no CPF via cadastro
de campo (clientes_cadastro); no futuro o app do cliente chega no CPF pelo
proprio login (cliente que so existe no SGP tambem funciona).

Cadastro de campo (clientes_cadastro) e opcional: so da o CPF e o serial de
fallback quando existe. Senha write-only -> confirmacao otimista (sem read-back).

Obs: pra o PPPoE resolver, o GenieACS precisa ter lido o WANPPPConnection.Username
do device (preset/refresh). Enquanto isso nao estiver provisionado, o serial
fallback cobre (o tecnico tem o serial na instalacao).
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
from ondeline_api.db.models.business import ClienteCadastro
from ondeline_api.db.models.rede import RedeWifiPedido

log = structlog.get_logger(__name__)

SENHA_MIN = 8
SENHA_MAX = 63


class GenieProto(Protocol):
    async def find_device_by_pppoe(self, login: str) -> GenieAcsDevice | None: ...
    async def find_device_by_serial(self, serial: str) -> GenieAcsDevice | None: ...
    async def set_parameter_values(
        self, device_id: str, params: list[tuple[str, str, str]]
    ) -> None: ...
    async def reboot(self, device_id: str) -> None: ...


class SgpCacheProto(Protocol):
    async def get_cliente(self, cpf: str) -> ClienteSgp | None: ...


class SenhaInvalidaError(ValueError):
    """Senha fora do range WPA-PSK (8-63 chars ASCII imprimivel)."""


class OnuNaoEncontradaError(Exception):
    """Nao foi possivel resolver a ONU (sem PPPoE no GenieACS e sem serial)."""


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


@dataclass(frozen=True, slots=True)
class _Resolucao:
    """Resultado da resolucao da ONU + dados de auditoria associados."""

    device: GenieAcsDevice | None
    pppoe: str | None
    contrato_id: str | None


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
        genieacs: GenieProto,
        sgp_cache: SgpCacheProto,
    ) -> None:
        self._session = session
        self._genie = genieacs
        self._sgp = sgp_cache

    async def _cpf_serial_do_cadastro(
        self, cadastro_id: UUID
    ) -> tuple[str | None, str | None]:
        """Pega (cpf, serial) do cadastro de campo, se existir.

        Cliente sem cadastro de campo (so no SGP) retorna (None, None) e a
        resolucao depende do serial digitado pelo tecnico OU, no fluxo do app
        cliente, do CPF vindo do login (que e passado direto a _resolver_por_cpf).
        """
        cad = (
            await self._session.execute(
                select(ClienteCadastro).where(ClienteCadastro.id == cadastro_id)
            )
        ).scalar_one_or_none()
        if cad is None:
            return None, None
        return decrypt_pii(cad.cpf_encrypted), cad.serial

    async def _resolver_por_cpf(self, cpf: str | None, serial: str | None) -> _Resolucao:
        """Core reusavel: CPF -> SGP -> contrato -> pppoe -> device.

        O SGP e a fonte do PPPoE (todos os clientes). PPPoE e a chave PRINCIPAL;
        serial e o fallback. Reusado pelo app do cliente no futuro (passa o CPF
        do login direto, sem cadastro de campo).
        """
        pppoe: str | None = None
        contrato_id: str | None = None
        if cpf:
            cli = await self._sgp.get_cliente(cpf)
            contrato = _primeiro_contrato(cli.contratos) if cli else None
            if contrato is not None:
                pppoe = contrato.pppoe_login or None
                contrato_id = contrato.id or None

        device: GenieAcsDevice | None = None
        if pppoe:
            device = await self._genie.find_device_by_pppoe(pppoe)
        if device is None and serial:
            device = await self._genie.find_device_by_serial(serial)
        return _Resolucao(device=device, pppoe=pppoe, contrato_id=contrato_id)

    async def _resolver_por_cadastro(
        self, cadastro_id: UUID, serial_manual: str | None
    ) -> _Resolucao:
        cpf, serial_cad = await self._cpf_serial_do_cadastro(cadastro_id)
        return await self._resolver_por_cpf(cpf, serial_manual or serial_cad)

    async def status_rede(
        self, cadastro_id: UUID, serial: str | None = None
    ) -> StatusRede:
        res = await self._resolver_por_cadastro(cadastro_id, serial)
        if res.device is None:
            return StatusRede(
                encontrada=False, pppoe_login=res.pppoe, motivo="onu_nao_encontrada"
            )
        return StatusRede(encontrada=True, device=res.device, pppoe_login=res.pppoe)

    async def trocar_senha_wifi(
        self,
        *,
        cadastro_id: UUID,
        nova_senha: str,
        serial: str | None,
        ator_user_id: UUID,
    ) -> ResultadoTroca:
        _validar_senha(nova_senha)
        res = await self._resolver_por_cadastro(cadastro_id, serial)
        if res.device is None:
            raise OnuNaoEncontradaError("ONU nao encontrada por PPPoE nem serial")

        plano = montar_plano(res.device, nova_senha)

        # Registra ANTES do envio (status=pendente) e da flush: auditoria de
        # troca de senha nao pode perder uma troca que JA aplicou na ONU. Se o
        # envio falhar (GenieAcsUnavailableError), o registro sobrevive como
        # 'pendente' e o erro propaga. So depois do envio OK vira 'enviado'.
        pedido = RedeWifiPedido(
            cliente_id=cadastro_id,
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
            cadastro_id=str(cadastro_id),
            device_id=res.device.device_id,
            redes=len(plano.params),
            reboot=plano.needs_reboot,
        )
        return ResultadoTroca(
            device_id=res.device.device_id, reiniciando=plano.needs_reboot
        )
