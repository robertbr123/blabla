"""F6 — Serviço de estoque: regras de movimentação.

Modelo: `tecnico_id` em EstoqueMovimento eh nullable.
- `tecnico_id IS NULL` -> movimento eh do DEPOSITO central
- `tecnico_id = X`     -> movimento eh do estoque pessoal do tecnico X

Regras (validadas por `registrar_movimento`):
  - Item deve existir e estar ativo.
  - Quantidade > 0 (CHECK constraint reforça no banco).
  - Itens serializados exigem `serial` informado; um serial não pode ter
    saldo > 1 no mesmo "local" (deposito OU mesmo tecnico).
  - Tipos negativos (saida/devolucao/perda/ajuste_negativo) exigem saldo
    suficiente no local de origem — senão erro `SaldoInsuficiente`.

Operações de alto nível:
  - `registrar_movimento(...)` — primitiva (1 movimento)
  - `transferir_deposito_para_tecnico(...)` — atomico: 2 movimentos
    (saida do deposito + entrada no tecnico)
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.estoque import (
    TIPOS_POSITIVOS,
    EstoqueItem,
    EstoqueMovimento,
    MovimentoTipo,
)
from ondeline_api.repositories.estoque import ItemRepo, MovimentoRepo

log = structlog.get_logger(__name__)


class EstoqueError(Exception):
    """Erro de regra de negócio do estoque."""


class SaldoInsuficiente(EstoqueError):
    pass


class ItemNaoExiste(EstoqueError):
    pass


class SerialDuplicado(EstoqueError):
    pass


_TIPOS_NEGATIVOS = {
    MovimentoTipo.SAIDA.value,
    MovimentoTipo.DEVOLUCAO.value,
    MovimentoTipo.PERDA.value,
    MovimentoTipo.AJUSTE_NEGATIVO.value,
}


async def registrar_movimento(
    session: AsyncSession,
    *,
    item_id: UUID,
    tipo: str,
    quantidade: int,
    criado_por: UUID,
    tecnico_id: UUID | None = None,
    serial: str | None = None,
    ordem_servico_id: UUID | None = None,
    cliente_cadastro_id: UUID | None = None,
    observacao: str | None = None,
) -> EstoqueMovimento:
    if quantidade <= 0:
        raise EstoqueError("quantidade deve ser > 0")
    if tipo not in {t.value for t in MovimentoTipo}:
        raise EstoqueError(f"tipo invalido: {tipo}")

    item = await ItemRepo(session).get_by_id(item_id)
    if item is None or not item.ativo:
        raise ItemNaoExiste("item inexistente ou inativo")

    if item.serializado:
        if not serial:
            raise EstoqueError("item serializado exige `serial`")
        if quantidade != 1:
            raise EstoqueError("item serializado exige quantidade=1")

    movrepo = MovimentoRepo(session)

    # Para tipos negativos, valida saldo no local de origem (deposito ou
    # tecnico — `tecnico_id=None` significa o deposito central).
    if tipo in _TIPOS_NEGATIVOS:
        saldo = await movrepo.saldo_por_local_item(tecnico_id, item_id)
        if saldo < quantidade:
            local = "deposito" if tecnico_id is None else "tecnico"
            raise SaldoInsuficiente(
                f"saldo insuficiente no {local}: tem {saldo}, precisa {quantidade}"
            )

    # Para tipos positivos com serial, verifica se o serial AINDA esta em
    # estoque. Soma com sinal sobre movimentos do serial — imune a ambiguidade
    # de timestamp identico entre movimentos.
    if item.serializado and serial and tipo in TIPOS_POSITIVOS:
        saldo_serial = await movrepo.saldo_do_serial(item_id, serial)
        if saldo_serial > 0:
            raise SerialDuplicado(
                f"serial {serial} ja em estoque (saldo {saldo_serial})"
            )

    mov = EstoqueMovimento(
        item_id=item_id,
        tecnico_id=tecnico_id,
        tipo=tipo,
        quantidade=quantidade,
        serial=serial,
        ordem_servico_id=ordem_servico_id,
        cliente_cadastro_id=cliente_cadastro_id,
        observacao=observacao,
        criado_por=criado_por,
    )
    await movrepo.insert(mov)

    # F8 — Histórico de equipamentos do cliente.
    # Saída com serial + OS (ou cliente_cadastro) = cliente recebeu o equipamento.
    # Recolhido com serial = cliente devolveu → fecha o registro ativo.
    if item.serializado and serial:
        await _atualizar_cliente_equipamento(
            session,
            tipo=tipo,
            item_id=item_id,
            serial=serial,
            ordem_servico_id=ordem_servico_id,
            cliente_cadastro_id=cliente_cadastro_id,
            tecnico_id=tecnico_id,
        )

    from ondeline_api.observability.metrics import (
        estoque_movimento_total,
    )

    estoque_movimento_total.labels(tipo=tipo).inc()
    log.info(
        "estoque.movimento.registrado",
        item_id=str(item_id),
        tecnico_id=str(tecnico_id) if tecnico_id else None,
        tipo=tipo,
        quantidade=quantidade,
        serial=serial,
        os_id=str(ordem_servico_id) if ordem_servico_id else None,
    )
    return mov


async def transferir_deposito_para_tecnico(
    session: AsyncSession,
    *,
    item_id: UUID,
    tecnico_id: UUID,
    quantidade: int,
    criado_por: UUID,
    serial: str | None = None,
    observacao: str | None = None,
) -> tuple[EstoqueMovimento, EstoqueMovimento]:
    """Transferência atômica: depósito -> técnico.

    Cria 2 movimentos no mesmo flush:
    1. (tecnico_id=NULL, tipo=saida)    — sai do depósito
    2. (tecnico_id=X,    tipo=entrada)  — entra no técnico

    Se saldo do depósito for insuficiente, levanta SaldoInsuficiente
    antes de gravar qualquer coisa.
    """
    obs_suffix = f"transferencia → tecnico {tecnico_id}"
    obs_in = obs_suffix if not observacao else f"{observacao} | {obs_suffix}"

    saida = await registrar_movimento(
        session,
        item_id=item_id,
        tipo=MovimentoTipo.SAIDA.value,
        quantidade=quantidade,
        criado_por=criado_por,
        tecnico_id=None,
        serial=serial,
        observacao=obs_in,
    )
    entrada = await registrar_movimento(
        session,
        item_id=item_id,
        tipo=MovimentoTipo.ENTRADA.value,
        quantidade=quantidade,
        criado_por=criado_por,
        tecnico_id=tecnico_id,
        serial=serial,
        observacao=obs_in,
    )
    return saida, entrada


async def calcular_saldo_tecnico(
    session: AsyncSession, tecnico_id: UUID
) -> list[dict[str, Any]]:
    """Retorna lista de dicts com `item` + `saldo` pra cada item ativo."""
    rows = await MovimentoRepo(session).saldo_full_por_tecnico(tecnico_id)
    return [
        {
            "item_id": str(item.id),
            "sku": item.sku,
            "nome": item.nome,
            "categoria": item.categoria,
            "serializado": item.serializado,
            "saldo": saldo,
        }
        for item, saldo in rows
    ]


def upsert_item(
    session: AsyncSession,
    *,
    sku: str,
    nome: str,
    categoria: str,
    serializado: bool = False,
) -> EstoqueItem:
    """Helper construtivo (não persiste sozinho)."""
    return EstoqueItem(
        sku=sku, nome=nome, categoria=categoria, serializado=serializado
    )


async def _atualizar_cliente_equipamento(
    session: AsyncSession,
    *,
    tipo: str,
    item_id: UUID,
    serial: str,
    ordem_servico_id: UUID | None,
    cliente_cadastro_id: UUID | None = None,
    tecnico_id: UUID | None,
) -> None:
    """Hook do F8: mantém cliente_equipamento sincronizado com os movimentos.

    - saida com ordem_servico_id → cria registro (descobre cliente via OS).
    - saida com cliente_cadastro_id → cria registro vinculado ao cadastro
      em campo (cruza com Cliente SGP pelo cpf_hash se houver).
    - recolhido → fecha registro ATIVO daquele item+serial (se houver).
    - outros tipos → ignora.

    Falha silenciosa (log warning) — não derruba o registro do movimento.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from ondeline_api.db.models.business import Cliente, ClienteCadastro, OrdemServico
    from ondeline_api.db.models.estoque import ClienteEquipamento
    from ondeline_api.repositories.cliente_equipamento import (
        ClienteEquipamentoRepo,
    )

    repo = ClienteEquipamentoRepo(session)

    if tipo == "saida":
        # 1) Caso OS: descobre cliente pela OS
        cliente_id: UUID | None = None
        if ordem_servico_id is not None:
            os_row = (
                await session.execute(
                    select(OrdemServico).where(OrdemServico.id == ordem_servico_id)
                )
            ).scalar_one_or_none()
            if os_row is not None:
                cliente_id = os_row.cliente_id

        # 2) Caso cadastro em campo: cruza cpf_hash com Cliente SGP
        if cliente_id is None and cliente_cadastro_id is not None:
            cc_row = (
                await session.execute(
                    select(ClienteCadastro).where(
                        ClienteCadastro.id == cliente_cadastro_id
                    )
                )
            ).scalar_one_or_none()
            if cc_row is not None:
                sgp_cli = (
                    await session.execute(
                        select(Cliente).where(
                            Cliente.cpf_hash == cc_row.cpf_hash,
                            Cliente.deleted_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if sgp_cli is not None:
                    cliente_id = sgp_cli.id

        if cliente_id is None:
            log.info(
                "cliente_equipamento.skip_sem_cliente",
                ordem_servico_id=str(ordem_servico_id) if ordem_servico_id else None,
                cliente_cadastro_id=str(cliente_cadastro_id) if cliente_cadastro_id else None,
            )
            return

        # Evita duplicar — se já tem ativo pra esse serial, fecha antes.
        existente = await repo.find_ativo_por_serial(item_id, serial)
        if existente is not None:
            existente.removido_em = datetime.now(tz=UTC)
            existente.removido_em_os_id = ordem_servico_id
            await session.flush()
        novo = ClienteEquipamento(
            cliente_id=cliente_id,
            item_id=item_id,
            serial=serial,
            instalado_em_os_id=ordem_servico_id,
            instalado_por_tecnico_id=tecnico_id,
        )
        session.add(novo)
        try:
            await session.flush()
        except Exception as e:
            log.warning(
                "cliente_equipamento.insert_falhou",
                serial=serial,
                error=str(e),
            )
        return

    if tipo == "recolhido":
        existente = await repo.find_ativo_por_serial(item_id, serial)
        if existente is None:
            log.info(
                "cliente_equipamento.recolhido_sem_registro_ativo",
                serial=serial,
            )
            return
        existente.removido_em = datetime.now(tz=UTC)
        existente.removido_em_os_id = ordem_servico_id
        await session.flush()
