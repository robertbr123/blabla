"""F6 — Serviço de estoque: regras de movimentação.

Regras (validadas por `registrar_movimento`):
  - Item deve existir e estar ativo.
  - Quantidade > 0 (CHECK constraint reforça no banco).
  - Itens serializados exigem `serial` informado; um serial não pode ter
    saldo > 1 no mesmo técnico ao mesmo tempo (caso usuario tente entrada
    duplicada do mesmo serial).
  - Tipos negativos (saida/devolucao/perda/ajuste_negativo) exigem saldo
    suficiente — senão erro `SaldoInsuficiente`.
  - `tecnico_id` é obrigatório para tipos negativos (não pode dar baixa
    de "almoxarifado") — admin reflete movimento sempre por técnico.
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

    if tipo in _TIPOS_NEGATIVOS:
        if tecnico_id is None:
            raise EstoqueError(
                "tipos saida/devolucao/perda/ajuste_negativo exigem tecnico_id"
            )

    movrepo = MovimentoRepo(session)

    # Para tipos negativos, valida saldo do técnico.
    if tipo in _TIPOS_NEGATIVOS:
        assert tecnico_id is not None  # narrow pra typer
        saldo = await movrepo.saldo_por_tecnico_item(tecnico_id, item_id)
        if saldo < quantidade:
            raise SaldoInsuficiente(
                f"saldo insuficiente: tem {saldo}, precisa {quantidade}"
            )

    # Para tipos positivos com serial, verifica se ja nao tem +saldo desse serial.
    if item.serializado and serial and tipo in TIPOS_POSITIVOS:
        ultimo = await movrepo.ultimo_movimento_serial(item_id, serial)
        if ultimo is not None and ultimo.tipo in TIPOS_POSITIVOS:
            raise SerialDuplicado(
                f"serial {serial} ja em estoque (movimento {ultimo.id})"
            )

    mov = EstoqueMovimento(
        item_id=item_id,
        tecnico_id=tecnico_id,
        tipo=tipo,
        quantidade=quantidade,
        serial=serial,
        ordem_servico_id=ordem_servico_id,
        observacao=observacao,
        criado_por=criado_por,
    )
    await movrepo.insert(mov)

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
