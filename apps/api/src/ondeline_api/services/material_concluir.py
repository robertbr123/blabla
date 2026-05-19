"""F6+ — Parsing de materiais informados pelo técnico no fluxo CONCLUIR via WhatsApp.

Tecnico digita texto livre tipo "2 conector, 100m cabo, 1 onu" e a gente:
  1. Quebra em itens.
  2. Para cada item, extrai quantidade + nome.
  3. Casa o nome contra o estoque do técnico (saldo > 0) com fuzzy match:
     a) match exato em sku ou nome
     b) substring em nome
     c) substring na categoria
  4. Devolve lista de matches + lista de não-encontrados.

NÃO baixa estoque aqui — só prepara a lista. Caller decide se confirma.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.estoque import EstoqueItem
from ondeline_api.repositories.estoque import MovimentoRepo


@dataclass(frozen=True, slots=True)
class MaterialMatch:
    """Item casado no estoque do técnico, com quantidade e saldo disponível.

    `serial` é preenchido depois (passo de coleta de serial) só para itens
    serializados. Para os demais, fica None.
    """

    item_id: UUID
    sku: str
    nome: str
    categoria: str
    serializado: bool
    quantidade: int
    saldo_atual: int  # snapshot pra mostrar antes de confirmar
    nome_digitado: str
    serial: str | None = None


@dataclass(frozen=True, slots=True)
class MaterialParseResult:
    matches: list[MaterialMatch]
    nao_encontrados: list[str]  # textos crus que não casaram
    invalidos: list[str]        # itens que não passaram no regex
    sem_saldo: list[tuple[str, int, int]]  # (nome_digitado, qty, saldo_disponivel)


_UNIDADES = r"(?:m|metros?|cm|un|unidade|unidades|pe[çc]as?|pcs?|x)?"
# Regex: captura quantidade (inteiro ou decimal) + nome.
# Ex: "2 conector", "10m cabo utp", "1 onu", "2x roteador"
_RE_LINHA = re.compile(
    r"^\s*(\d+)(?:[.,]\d+)?\s*" + _UNIDADES + r"\s+(.+?)\s*$",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _split_input(text: str) -> list[str]:
    """Quebra por vírgula, ponto-e-vírgula, 'e', newline."""
    parts = re.split(r"[,;\n]+|\s+e\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_linha(linha: str) -> tuple[int, str] | None:
    m = _RE_LINHA.match(linha)
    if not m:
        return None
    qty = int(m.group(1))
    nome = m.group(2).strip()
    if qty <= 0 or not nome:
        return None
    return qty, nome


def _fuzzy_match(nome: str, catalogo_com_saldo: list[tuple[EstoqueItem, int]]) -> tuple[EstoqueItem, int] | None:
    """Casa `nome` digitado contra itens que o técnico TEM em estoque (saldo > 0).

    Ordem de preferência:
      1) match exato no SKU (case-insensitive)
      2) match exato no nome
      3) nome digitado é substring do nome do item
      4) nome digitado casa a categoria do item
      5) qualquer palavra do nome digitado é substring do nome do item
    """
    digit = _normalize(nome)
    if not digit:
        return None

    # 1) SKU exato
    for it, saldo in catalogo_com_saldo:
        if _normalize(it.sku) == digit:
            return it, saldo
    # 2) Nome exato
    for it, saldo in catalogo_com_saldo:
        if _normalize(it.nome) == digit:
            return it, saldo
    # 3) Digitado é substring do nome
    for it, saldo in catalogo_com_saldo:
        if digit in _normalize(it.nome):
            return it, saldo
    # 4) Match de categoria
    for it, saldo in catalogo_com_saldo:
        if digit == _normalize(it.categoria):
            return it, saldo
    # 5) Qualquer palavra do digitado bate
    palavras = [p for p in digit.split() if len(p) >= 3]
    for it, saldo in catalogo_com_saldo:
        nome_it = _normalize(it.nome)
        if any(p in nome_it for p in palavras):
            return it, saldo
    return None


async def parse_e_casar_materiais(
    session: AsyncSession,
    *,
    tecnico_id: UUID,
    texto: str,
) -> MaterialParseResult:
    """Recebe o texto livre do técnico e devolve o que casou com o estoque dele."""
    # Saldo atual do técnico (itens com saldo > 0).
    repo = MovimentoRepo(session)
    saldo_full = await repo.saldo_full_por_tecnico(tecnico_id)
    catalogo_com_saldo = [(it, saldo) for it, saldo in saldo_full if saldo > 0]

    linhas = _split_input(texto)
    matches: list[MaterialMatch] = []
    nao_encontrados: list[str] = []
    invalidos: list[str] = []
    sem_saldo: list[tuple[str, int, int]] = []

    for linha in linhas:
        parsed = _parse_linha(linha)
        if parsed is None:
            invalidos.append(linha)
            continue
        qty, nome_digitado = parsed
        cand = _fuzzy_match(nome_digitado, catalogo_com_saldo)
        if cand is None:
            nao_encontrados.append(f"{qty}x {nome_digitado}")
            continue
        item, saldo = cand
        if qty > saldo:
            sem_saldo.append((nome_digitado, qty, saldo))
            continue
        # Itens serializados só aceitam qty=1 — bot perguntará o serial num
        # passo separado. Se técnico digitar "3 onu", ele divide em 3 entradas
        # ou marca como inválido pra ele corrigir.
        if item.serializado and qty != 1:
            invalidos.append(
                f"{qty}x {item.nome} (serializado — registre 1 por vez)"
            )
            continue
        matches.append(
            MaterialMatch(
                item_id=item.id,
                sku=item.sku,
                nome=item.nome,
                categoria=item.categoria,
                serializado=item.serializado,
                quantidade=qty,
                saldo_atual=saldo,
                nome_digitado=nome_digitado,
            )
        )

    return MaterialParseResult(
        matches=matches,
        nao_encontrados=nao_encontrados,
        invalidos=invalidos,
        sem_saldo=sem_saldo,
    )


def render_lista_estoque(catalogo_com_saldo: list[tuple[EstoqueItem, int]]) -> str:
    """Texto pra mostrar pro técnico no WhatsApp: lista dos itens dele com saldo."""
    if not catalogo_com_saldo:
        return "_(seu estoque está vazio)_"
    linhas = []
    for it, saldo in catalogo_com_saldo:
        if saldo > 0:
            linhas.append(f"• {it.nome} ({saldo})")
    return "\n".join(linhas) if linhas else "_(sem itens com saldo)_"


def render_resumo_baixa(matches: list[MaterialMatch]) -> str:
    if not matches:
        return "_(nada a baixar)_"
    linhas = []
    for m in matches:
        linha = f"• {m.quantidade}x {m.nome}"
        if m.serial:
            linha += f" — serial `{m.serial}`"
        linhas.append(linha)
    return "\n".join(linhas)


def render_resumo_baixa_dict(matches: list[dict[str, Any]]) -> str:
    """Mesma função, mas pra lista de dicts (versão serializada do metadata)."""
    if not matches:
        return "_(nada a baixar)_"
    linhas = []
    for m in matches:
        linha = f"• {m['quantidade']}x {m['nome']}"
        if m.get("serial"):
            linha += f" — serial `{m['serial']}`"
        linhas.append(linha)
    return "\n".join(linhas)
