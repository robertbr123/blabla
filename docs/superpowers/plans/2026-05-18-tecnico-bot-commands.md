# Comandos de Técnico via WhatsApp — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar comandos OS / RESUMO / AJUDA no inbound do bot WhatsApp para que técnicos cadastrados recebam respostas operacionais (lista de OS, contagens, ajuda) em vez de cair no fluxo de cliente. Migra CONCLUIR existente para o mesmo módulo novo.

**Architecture:** Novo módulo `services/tecnico_inbound.py` que identifica técnico pelo JID (lookup com normalização de telefone BR) e despacha comandos. `inbound.py` chama o dispatcher entre os blocos `CHECKLIST_OS` e `bot.ativo` — técnicos retornam cedo, clientes seguem o fluxo normal. Repositórios ganham métodos focados em consultas do técnico.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, structlog, pytest-asyncio. Sem migration, sem mudança de modelo, sem frontend.

**Spec:** `docs/superpowers/specs/2026-05-18-tecnico-bot-commands-design.md`

---

## Arquivos afetados

**Novos:**
- `apps/api/src/ondeline_api/services/phone.py` — utilitário de normalização e formatação de telefone BR (extrai `_br_local_digits` do `inbound.py`).
- `apps/api/src/ondeline_api/services/tecnico_inbound.py` — dispatcher e handlers de comandos de técnico.
- `apps/api/tests/test_phone.py`
- `apps/api/tests/test_tecnico_inbound.py`
- `apps/api/tests/test_inbound_tecnico_routing.py`

**Modificados:**
- `apps/api/src/ondeline_api/repositories/tecnico.py` — adiciona `get_by_jid`.
- `apps/api/src/ondeline_api/repositories/ordem_servico.py` — adiciona `list_ativas_by_tecnico`, `count_by_status_for_tecnico`, `proxima_agendada`.
- `apps/api/src/ondeline_api/services/inbound.py` — remove bloco CONCLUIR inline, adiciona chamada ao dispatcher; remove `_br_local_digits` local.

---

## Task 1: Utilitário compartilhado de telefone

**Files:**
- Create: `apps/api/src/ondeline_api/services/phone.py`
- Create: `apps/api/tests/test_phone.py`

- [ ] **Step 1.1: Write the failing tests**

Create `apps/api/tests/test_phone.py`:

```python
"""Testes de normalização e formatação de telefone BR."""
from __future__ import annotations

import pytest
from ondeline_api.services.phone import br_local_digits, format_br_phone


def test_br_local_digits_strips_country_code() -> None:
    assert br_local_digits("559784109856") == "84109856"


def test_br_local_digits_strips_country_and_ninth_digit() -> None:
    assert br_local_digits("5597984109856") == "84109856"


def test_br_local_digits_strips_ddd_only() -> None:
    assert br_local_digits("97984109856") == "84109856"


def test_br_local_digits_already_local() -> None:
    assert br_local_digits("84109856") == "84109856"


def test_br_local_digits_handles_non_digit_input() -> None:
    # Caller é responsável por strip; função aceita só dígitos
    assert br_local_digits("") == ""


def test_format_br_phone_full_with_ninth_digit() -> None:
    assert format_br_phone("5597984109856") == "(97) 9 8410-9856"


def test_format_br_phone_without_country_code() -> None:
    assert format_br_phone("97984109856") == "(97) 9 8410-9856"


def test_format_br_phone_eight_digit_local() -> None:
    # Sem DDD/9° dígito conhecidos — devolve "como está" formatado
    assert format_br_phone("84109856") == "8410-9856"


def test_format_br_phone_with_punctuation_input() -> None:
    assert format_br_phone("(97) 9 8410-9856") == "(97) 9 8410-9856"


def test_format_br_phone_empty_returns_empty() -> None:
    assert format_br_phone("") == ""
    assert format_br_phone(None) == ""
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_phone.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ondeline_api.services.phone'`

- [ ] **Step 1.3: Implement `services/phone.py`**

Create `apps/api/src/ondeline_api/services/phone.py`:

```python
"""Utilitários de telefone brasileiro.

Normalização e formatação para uso em matching (técnico/cliente por JID)
e display (lista de OS para técnico). Extraído de `services/inbound.py`
quando começou a ser usado em mais de um lugar.
"""
from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\D")


def br_local_digits(digits: str) -> str:
    """Normaliza dígitos de número BR para os 8 dígitos locais.

    Tolera: com/sem código de país (55), com/sem DDD, com/sem nono dígito.
    Ex: "559784109856" → "84109856"
        "5597984109856" → "84109856"
        "97984109856" → "84109856"
    Entrada deve ser só dígitos (caller usa _DIGITS_RE.sub se necessário).
    """
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = digits[2:]
    if len(digits) == 9 and digits[0] == "9":
        digits = digits[1:]
    return digits


def format_br_phone(raw: str | None) -> str:
    """Formata telefone BR para display: "(DD) 9 XXXX-XXXX".

    Aceita qualquer entrada com lixo (parênteses, espaços, hífens, +55).
    Se o número não tiver DDD reconhecível, devolve só o local "XXXX-XXXX".
    """
    if not raw:
        return ""
    d = _DIGITS_RE.sub("", raw)
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) == 11:
        # DDD + 9° dígito: 97 9 8410 9856
        return f"({d[0:2]}) {d[2]} {d[3:7]}-{d[7:11]}"
    if len(d) == 10:
        # DDD sem 9°: 97 8410 9856
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) == 9 and d[0] == "9":
        # 9° dígito + 8 locais, sem DDD
        return f"{d[0]} {d[1:5]}-{d[5:9]}"
    if len(d) == 8:
        return f"{d[0:4]}-{d[4:8]}"
    return raw  # fallback: devolve original
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_phone.py -v`
Expected: PASS (10 tests)

- [ ] **Step 1.5: Commit**

```bash
git add apps/api/src/ondeline_api/services/phone.py apps/api/tests/test_phone.py
git commit -m "feat(phone): utilitario compartilhado de normalizacao e formatacao BR"
```

---

## Task 2: `TecnicoRepo.get_by_jid`

**Files:**
- Modify: `apps/api/src/ondeline_api/repositories/tecnico.py` (adicionar método)
- Test: usa testes do módulo `tecnico_inbound` (Task 7) que cobrem o lookup ponta a ponta. Aqui adicionamos teste isolado também.
- Create test: `apps/api/tests/test_repo_tecnico_get_by_jid.py`

- [ ] **Step 2.1: Write the failing test**

Create `apps/api/tests/test_repo_tecnico_get_by_jid.py`:

```python
"""TecnicoRepo.get_by_jid — lookup por número WhatsApp normalizado."""
from __future__ import annotations

import pytest
from ondeline_api.repositories.tecnico import TecnicoRepo

pytestmark = pytest.mark.asyncio


async def test_get_by_jid_matches_with_country_code(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="João", whatsapp="5597984109856", ativo=True)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is not None
    assert found.nome == "João"


async def test_get_by_jid_matches_with_local_digits(db_session) -> None:
    repo = TecnicoRepo(db_session)
    # Técnico cadastrado SEM código de país
    await repo.create(nome="Maria", whatsapp="97984109856", ativo=True)
    # JID chega com código de país (formato Evolution)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is not None
    assert found.nome == "Maria"


async def test_get_by_jid_ignores_inactive(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="Inativo", whatsapp="5597984109856", ativo=False)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is None


async def test_get_by_jid_returns_none_when_not_found(db_session) -> None:
    repo = TecnicoRepo(db_session)
    found = await repo.get_by_jid("5597999999999@s.whatsapp.net")
    assert found is None


async def test_get_by_jid_returns_none_for_tecnico_without_whatsapp(db_session) -> None:
    repo = TecnicoRepo(db_session)
    await repo.create(nome="SemTel", whatsapp=None, ativo=True)
    found = await repo.get_by_jid("5597984109856@s.whatsapp.net")
    assert found is None
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_repo_tecnico_get_by_jid.py -v`
Expected: FAIL with `AttributeError: 'TecnicoRepo' object has no attribute 'get_by_jid'`

- [ ] **Step 2.3: Implement `get_by_jid`**

Edit `apps/api/src/ondeline_api/repositories/tecnico.py`. Adicionar import no topo:

```python
import re

from ondeline_api.services.phone import br_local_digits
```

Adicionar método na classe `TecnicoRepo` (após `find_by_area`):

```python
    async def get_by_jid(self, jid: str) -> Tecnico | None:
        """Lookup de técnico por JID do WhatsApp.

        Normaliza o JID para os 8 dígitos locais BR e procura técnico ATIVO
        cujo whatsapp normalizado coincida. Tolera variações de DDD/9° dígito
        entre cadastro e JID que vem da Evolution API.
        """
        jid_local = br_local_digits(re.sub(r"\D", "", jid or ""))
        if len(jid_local) != 8:
            return None
        stmt = select(Tecnico).where(
            Tecnico.ativo.is_(True), Tecnico.whatsapp.isnot(None)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        for t in rows:
            t_local = br_local_digits(re.sub(r"\D", "", t.whatsapp or ""))
            if len(t_local) == 8 and t_local == jid_local:
                return t
        return None
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_repo_tecnico_get_by_jid.py -v`
Expected: PASS (5 tests)

- [ ] **Step 2.5: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/tecnico.py apps/api/tests/test_repo_tecnico_get_by_jid.py
git commit -m "feat(tecnico-repo): add get_by_jid com normalizacao BR"
```

---

## Task 3: `OrdemServicoRepo.list_ativas_by_tecnico`

**Files:**
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Create test: `apps/api/tests/test_repo_os_tecnico_queries.py`

- [ ] **Step 3.1: Write the failing test**

Create `apps/api/tests/test_repo_os_tecnico_queries.py`:

```python
"""Queries focadas em consultas do técnico (lista ativas, contagens, próxima)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from ondeline_api.db.models.business import OsStatus
from ondeline_api.repositories.cliente import ClienteRepo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo

pytestmark = pytest.mark.asyncio


async def _seed_cliente(db_session) -> tuple:
    """Cria cliente mínimo e retorna (id, ClienteRepo)."""
    repo = ClienteRepo(db_session)
    c = await repo.upsert_from_sgp(
        cpf_cnpj="00000000000",
        nome="Cliente Teste",
        whatsapp="5597912345678",
        endereco="Rua A 1",
        plano=None,
        sgp_provider=None,
        sgp_id=None,
        status=None,
        cidade=None,
    )
    return c.id


async def test_list_ativas_returns_pendente_and_em_andamento(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    os1 = await os_repo.create(
        codigo="OS-1", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    os2 = await os_repo.create(
        codigo="OS-2", cliente_id=cli_id, tecnico_id=tec.id,
        problema="y", endereco="Rua B 2",
    )
    await os_repo.update(os2, status=OsStatus.EM_ANDAMENTO.value)
    os3 = await os_repo.create(
        codigo="OS-3", cliente_id=cli_id, tecnico_id=tec.id,
        problema="z", endereco="Rua C 3",
    )
    await os_repo.update(os3, status=OsStatus.CONCLUIDA.value)

    ativas = await os_repo.list_ativas_by_tecnico(tec.id, limit=10)
    codigos = {o.codigo for o in ativas}
    assert codigos == {"OS-1", "OS-2"}


async def test_list_ativas_orders_by_agendamento_nulls_last(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    sem_agenda = await os_repo.create(
        codigo="OS-SEM", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    futura = await os_repo.create(
        codigo="OS-FUT", cliente_id=cli_id, tecnico_id=tec.id,
        problema="y", endereco="Rua B 2",
    )
    futura.agendamento_at = datetime.now(tz=UTC) + timedelta(hours=2)
    proxima = await os_repo.create(
        codigo="OS-PROX", cliente_id=cli_id, tecnico_id=tec.id,
        problema="z", endereco="Rua C 3",
    )
    proxima.agendamento_at = datetime.now(tz=UTC) + timedelta(minutes=30)
    await db_session.flush()

    ativas = await os_repo.list_ativas_by_tecnico(tec.id, limit=10)
    assert [o.codigo for o in ativas] == ["OS-PROX", "OS-FUT", "OS-SEM"]


async def test_list_ativas_respects_limit_plus_one(db_session) -> None:
    """limit=11 deve retornar até 11 — caller usa o 11º pra detectar 'tem mais'."""
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    for i in range(14):
        await os_repo.create(
            codigo=f"OS-{i:02d}", cliente_id=cli_id, tecnico_id=tec.id,
            problema="x", endereco="Rua A 1",
        )

    ativas = await os_repo.list_ativas_by_tecnico(tec.id, limit=11)
    assert len(ativas) == 11


async def test_list_ativas_empty_for_unknown_tecnico(db_session) -> None:
    os_repo = OrdemServicoRepo(db_session)
    ativas = await os_repo.list_ativas_by_tecnico(uuid4(), limit=10)
    assert ativas == []
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py -v`
Expected: FAIL with `AttributeError: 'OrdemServicoRepo' object has no attribute 'list_ativas_by_tecnico'`

- [ ] **Step 3.3: Implement `list_ativas_by_tecnico`**

Edit `apps/api/src/ondeline_api/repositories/ordem_servico.py`. Adicionar método na classe `OrdemServicoRepo`:

```python
    async def list_ativas_by_tecnico(
        self, tecnico_id: UUID, *, limit: int = 11
    ) -> list[OrdemServico]:
        """OS ativas (pendente/em_andamento) ordenadas por agendamento NULLS LAST.

        Usado pelo comando WhatsApp `OS`. Caller deve usar limit=N+1 quando
        quiser detectar "tem mais que N" sem query de COUNT.
        """
        from sqlalchemy import select
        from sqlalchemy.sql import nulls_last

        stmt = (
            select(OrdemServico)
            .where(
                OrdemServico.tecnico_id == tecnico_id,
                OrdemServico.status.in_(
                    [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
                ),
            )
            .order_by(nulls_last(OrdemServico.agendamento_at.asc()), OrdemServico.criada_em.asc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py -v`
Expected: PASS (4 tests)

- [ ] **Step 3.5: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/ordem_servico.py apps/api/tests/test_repo_os_tecnico_queries.py
git commit -m "feat(os-repo): list_ativas_by_tecnico ordenado por agendamento"
```

---

## Task 4: `OrdemServicoRepo.count_by_status_for_tecnico`

**Files:**
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Test: estende `apps/api/tests/test_repo_os_tecnico_queries.py`

- [ ] **Step 4.1: Write the failing test**

Append em `apps/api/tests/test_repo_os_tecnico_queries.py`:

```python
async def test_count_by_status_for_tecnico_returns_zeros(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)

    counts = await os_repo.count_by_status_for_tecnico(tec.id)
    assert counts == {"pendente": 0, "em_andamento": 0, "concluida_mes": 0}


async def test_count_by_status_for_tecnico_counts_correctly(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    # 3 pendentes
    for i in range(3):
        await os_repo.create(
            codigo=f"P-{i}", cliente_id=cli_id, tecnico_id=tec.id,
            problema="x", endereco="Rua A 1",
        )

    # 2 em andamento
    for i in range(2):
        o = await os_repo.create(
            codigo=f"A-{i}", cliente_id=cli_id, tecnico_id=tec.id,
            problema="x", endereco="Rua A 1",
        )
        await os_repo.update(o, status=OsStatus.EM_ANDAMENTO.value)

    # 4 concluídas neste mês
    for i in range(4):
        o = await os_repo.create(
            codigo=f"C-{i}", cliente_id=cli_id, tecnico_id=tec.id,
            problema="x", endereco="Rua A 1",
        )
        await os_repo.concluir(o)

    counts = await os_repo.count_by_status_for_tecnico(tec.id)
    assert counts == {"pendente": 3, "em_andamento": 2, "concluida_mes": 4}


async def test_count_concluidas_excludes_previous_month(db_session) -> None:
    """OS concluída no mês passado NÃO conta em concluida_mes."""
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    o = await os_repo.create(
        codigo="C-OLD", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    await os_repo.concluir(o)
    # Força concluida_em pro mês anterior
    o.concluida_em = datetime.now(tz=UTC).replace(day=1) - timedelta(days=1)
    await db_session.flush()

    counts = await os_repo.count_by_status_for_tecnico(tec.id)
    assert counts["concluida_mes"] == 0
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py::test_count_by_status_for_tecnico_returns_zeros -v`
Expected: FAIL com `AttributeError: ... 'count_by_status_for_tecnico'`

- [ ] **Step 4.3: Implement `count_by_status_for_tecnico`**

Edit `apps/api/src/ondeline_api/repositories/ordem_servico.py`. Adicionar método:

```python
    async def count_by_status_for_tecnico(
        self, tecnico_id: UUID
    ) -> dict[str, int]:
        """Contagem agregada usada no comando WhatsApp `RESUMO`.

        Retorna pendente, em_andamento (totais) e concluida_mes (concluídas
        a partir do dia 1 do mês corrente em UTC — alinhado com `concluida_em`
        que é gravado em UTC pelo repo).
        """
        from datetime import UTC, datetime
        from sqlalchemy import func, select

        first_of_month = datetime.now(tz=UTC).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        stmt = select(OrdemServico.status, func.count()).where(
            OrdemServico.tecnico_id == tecnico_id,
            OrdemServico.status.in_(
                [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
            ),
        ).group_by(OrdemServico.status)
        rows = list((await self._session.execute(stmt)).all())

        concluida_stmt = select(func.count()).where(
            OrdemServico.tecnico_id == tecnico_id,
            OrdemServico.status == OsStatus.CONCLUIDA,
            OrdemServico.concluida_em >= first_of_month,
        )
        concluida_mes = (await self._session.execute(concluida_stmt)).scalar_one() or 0

        result: dict[str, int] = {"pendente": 0, "em_andamento": 0, "concluida_mes": int(concluida_mes)}
        for status, count in rows:
            key = status.value if hasattr(status, "value") else str(status)
            if key in result:
                result[key] = int(count)
        return result
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py -v`
Expected: PASS (todos — 4 da task 3 + 3 da task 4 = 7)

- [ ] **Step 4.5: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/ordem_servico.py apps/api/tests/test_repo_os_tecnico_queries.py
git commit -m "feat(os-repo): count_by_status_for_tecnico agrega pendente/andamento/concluida_mes"
```

---

## Task 5: `OrdemServicoRepo.proxima_agendada`

**Files:**
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Test: estende `apps/api/tests/test_repo_os_tecnico_queries.py`

- [ ] **Step 5.1: Write the failing test**

Append em `apps/api/tests/test_repo_os_tecnico_queries.py`:

```python
async def test_proxima_agendada_returns_earliest_future(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    far = await os_repo.create(
        codigo="OS-FAR", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    far.agendamento_at = datetime.now(tz=UTC) + timedelta(days=3)

    near = await os_repo.create(
        codigo="OS-NEAR", cliente_id=cli_id, tecnico_id=tec.id,
        problema="y", endereco="Rua B 2",
    )
    near.agendamento_at = datetime.now(tz=UTC) + timedelta(hours=1)

    past = await os_repo.create(
        codigo="OS-PAST", cliente_id=cli_id, tecnico_id=tec.id,
        problema="z", endereco="Rua C 3",
    )
    past.agendamento_at = datetime.now(tz=UTC) - timedelta(hours=1)
    await db_session.flush()

    proxima = await os_repo.proxima_agendada(tec.id)
    assert proxima is not None
    assert proxima.codigo == "OS-NEAR"


async def test_proxima_agendada_none_when_only_unscheduled(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    await os_repo.create(
        codigo="OS-A", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    proxima = await os_repo.proxima_agendada(tec.id)
    assert proxima is None


async def test_proxima_agendada_ignores_concluida(db_session) -> None:
    tec_repo = TecnicoRepo(db_session)
    os_repo = OrdemServicoRepo(db_session)
    tec = await tec_repo.create(nome="T", whatsapp="5597984109856", ativo=True)
    cli_id = await _seed_cliente(db_session)

    o = await os_repo.create(
        codigo="OS-C", cliente_id=cli_id, tecnico_id=tec.id,
        problema="x", endereco="Rua A 1",
    )
    o.agendamento_at = datetime.now(tz=UTC) + timedelta(hours=1)
    await os_repo.concluir(o)

    proxima = await os_repo.proxima_agendada(tec.id)
    assert proxima is None
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py::test_proxima_agendada_returns_earliest_future -v`
Expected: FAIL com `AttributeError: ... 'proxima_agendada'`

- [ ] **Step 5.3: Implement `proxima_agendada`**

Adicionar método em `OrdemServicoRepo`:

```python
    async def proxima_agendada(self, tecnico_id: UUID) -> OrdemServico | None:
        """Próxima OS agendada do técnico (pendente/em_andamento, agendamento futuro)."""
        from datetime import UTC, datetime
        from sqlalchemy import select

        stmt = (
            select(OrdemServico)
            .where(
                OrdemServico.tecnico_id == tecnico_id,
                OrdemServico.status.in_(
                    [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
                ),
                OrdemServico.agendamento_at.isnot(None),
                OrdemServico.agendamento_at >= datetime.now(tz=UTC),
            )
            .order_by(OrdemServico.agendamento_at.asc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
```

- [ ] **Step 5.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_repo_os_tecnico_queries.py -v`
Expected: PASS (10 tests total)

- [ ] **Step 5.5: Commit**

```bash
git add apps/api/src/ondeline_api/repositories/ordem_servico.py apps/api/tests/test_repo_os_tecnico_queries.py
git commit -m "feat(os-repo): proxima_agendada para resumo do tecnico"
```

---

## Task 6: Formatadores do `tecnico_inbound`

**Files:**
- Create: `apps/api/src/ondeline_api/services/tecnico_inbound.py`
- Create: `apps/api/tests/test_tecnico_inbound_formatters.py`

Vamos isolar os formatadores (puros, sem session) numa task antes do dispatcher pra dar bons testes unitários.

- [ ] **Step 6.1: Write the failing tests**

Create `apps/api/tests/test_tecnico_inbound_formatters.py`:

```python
"""Formatadores puros do módulo tecnico_inbound — sem DB."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from ondeline_api.services.tecnico_inbound import (
    format_agendamento,
    format_os_block,
    format_resumo,
    AJUDA_TEXT,
    NO_OS_TEXT,
    RESUMO_VAZIO_TEXT,
)


# Mocks leves — usamos dataclass para evitar precisar do SQLAlchemy
@dataclass
class _OsRow:
    codigo: str
    status: str  # "pendente" | "em_andamento"
    problema: str
    endereco: str
    agendamento_at: datetime | None


@dataclass
class _ClienteRow:
    nome: str | None
    whatsapp: str | None


TZ_MANAUS = ZoneInfo("America/Manaus")


def test_format_os_block_completo() -> None:
    os_ = _OsRow(
        codigo="OS-1234", status="pendente", problema="Sem sinal de internet",
        endereco="Av. Brasil 100",
        agendamento_at=datetime.now(tz=TZ_MANAUS).replace(hour=14, minute=0, second=0, microsecond=0),
    )
    cli = _ClienteRow(nome="João Silva", whatsapp="5597984109856")
    block = format_os_block(os_, cli)
    assert "*OS-1234*" in block
    assert "🟡" in block
    assert "João Silva" in block
    assert "(97) 9 8410-9856" in block
    assert "Av. Brasil 100" in block
    assert "Sem sinal de internet" in block
    assert "hoje 14h" in block


def test_format_os_block_em_andamento_emoji() -> None:
    os_ = _OsRow(
        codigo="OS-1", status="em_andamento", problema="x", endereco="y",
        agendamento_at=None,
    )
    cli = _ClienteRow(nome="N", whatsapp=None)
    assert "🟠" in format_os_block(os_, cli)


def test_format_os_block_omits_telefone_quando_null() -> None:
    os_ = _OsRow(codigo="OS-1", status="pendente", problema="x", endereco="y", agendamento_at=None)
    cli = _ClienteRow(nome="N", whatsapp=None)
    block = format_os_block(os_, cli)
    assert "📞" not in block


def test_format_os_block_cliente_sem_nome() -> None:
    os_ = _OsRow(codigo="OS-1", status="pendente", problema="x", endereco="y", agendamento_at=None)
    cli = _ClienteRow(nome=None, whatsapp=None)
    assert "Cliente sem nome" in format_os_block(os_, cli)


def test_format_os_block_problema_truncado() -> None:
    long_problema = "a" * 100
    os_ = _OsRow(codigo="OS-1", status="pendente", problema=long_problema, endereco="y", agendamento_at=None)
    cli = _ClienteRow(nome="N", whatsapp=None)
    block = format_os_block(os_, cli)
    assert "…" in block
    assert len([line for line in block.splitlines() if "🔧" in line][0]) <= 80  # 60 + emoji + espaços


def test_format_os_block_sem_agenda() -> None:
    os_ = _OsRow(codigo="OS-1", status="pendente", problema="x", endereco="y", agendamento_at=None)
    cli = _ClienteRow(nome="N", whatsapp=None)
    assert "sem agenda" in format_os_block(os_, cli)


def test_format_agendamento_hoje() -> None:
    now = datetime.now(tz=TZ_MANAUS)
    futuro_hoje = now.replace(hour=15, minute=0, second=0, microsecond=0)
    if futuro_hoje <= now:
        futuro_hoje = now + timedelta(minutes=10)
    assert format_agendamento(futuro_hoje).startswith("hoje ")


def test_format_agendamento_amanha() -> None:
    amanha = datetime.now(tz=TZ_MANAUS) + timedelta(days=1)
    amanha = amanha.replace(hour=9, minute=0, second=0, microsecond=0)
    assert format_agendamento(amanha) == "amanhã 09h"


def test_format_agendamento_data_distante() -> None:
    futuro = datetime.now(tz=TZ_MANAUS) + timedelta(days=10)
    futuro = futuro.replace(hour=8, minute=0, second=0, microsecond=0)
    out = format_agendamento(futuro)
    assert out.endswith("08h")
    assert "/" in out  # formato DD/MM HHh


def test_format_agendamento_none() -> None:
    assert format_agendamento(None) == "sem agenda"


def test_format_resumo_completo() -> None:
    proxima = _OsRow(
        codigo="OS-1234", status="pendente", problema="x", endereco="y",
        agendamento_at=datetime.now(tz=TZ_MANAUS).replace(hour=14, minute=0, second=0, microsecond=0),
    )
    text = format_resumo(
        counts={"pendente": 5, "em_andamento": 2, "concluida_mes": 28},
        proxima=proxima,
    )
    assert "*Seu resumo*" in text
    assert "🟡 Pendentes: 5" in text
    assert "🟠 Em andamento: 2" in text
    assert "✅ Concluídas (mês): 28" in text
    assert "📅 Próxima agendada: OS-1234" in text


def test_format_resumo_sem_proxima() -> None:
    text = format_resumo(
        counts={"pendente": 1, "em_andamento": 0, "concluida_mes": 5},
        proxima=None,
    )
    assert "Próxima agendada" not in text


def test_format_resumo_vazio() -> None:
    text = format_resumo(
        counts={"pendente": 0, "em_andamento": 0, "concluida_mes": 0},
        proxima=None,
    )
    assert text == RESUMO_VAZIO_TEXT


def test_ajuda_text_lists_commands() -> None:
    assert "*OS*" in AJUDA_TEXT
    assert "*RESUMO*" in AJUDA_TEXT
    assert "*CONCLUIR" in AJUDA_TEXT


def test_no_os_text() -> None:
    assert "não tem OS ativas" in NO_OS_TEXT
```

- [ ] **Step 6.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound_formatters.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ondeline_api.services.tecnico_inbound'`

- [ ] **Step 6.3: Implement formatadores**

Create `apps/api/src/ondeline_api/services/tecnico_inbound.py`:

```python
"""Roteador e handlers de mensagens de técnico via WhatsApp.

Identifica técnico cadastrado pelo JID e despacha comandos:
- OS: lista até 10 OS ativas detalhadas
- RESUMO: contagens + próxima agendada
- AJUDA / MENU / HELP / ?: lista comandos
- CONCLUIR OS-XXXX: inicia checklist de 3 passos (migrado de inbound.py)

Mensagens de técnico que não casam com nenhum comando são ignoradas
silenciosamente — técnico nunca cai no fluxo de cliente.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from ondeline_api.services.phone import format_br_phone

_TZ = ZoneInfo("America/Manaus")
_MAX_PROBLEMA_LEN = 60
_OS_LIMIT = 10

STATUS_EMOJI: dict[str, str] = {
    "pendente": "🟡",
    "em_andamento": "🟠",
    "concluida": "✅",
    "cancelada": "🚫",
}

AJUDA_TEXT = (
    "*Comandos disponíveis:*\n"
    "\n"
    "📋 *OS* — lista suas OS ativas\n"
    "📊 *RESUMO* — visão geral (pendentes, andamento, concluídas no mês)\n"
    "✅ *CONCLUIR OS-1234* — finaliza uma OS (inicia checklist)\n"
    "\n"
    "_Ajuda a qualquer momento: envie AJUDA._"
)

NO_OS_TEXT = "Você não tem OS ativas no momento. 🎉"
RESUMO_VAZIO_TEXT = "Você ainda não tem OS atribuídas."


class _OsLike(Protocol):
    codigo: str
    status: Any  # OsStatus enum or str
    problema: str
    endereco: str
    agendamento_at: datetime | None


class _ClienteLike(Protocol):
    nome: str | None
    whatsapp: str | None


def _status_str(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


def format_agendamento(dt: datetime | None) -> str:
    """Formata agendamento como 'hoje HHh', 'amanhã HHh', 'DD/MM HHh' ou 'sem agenda'.

    Converte para America/Manaus antes de comparar dias.
    """
    if dt is None:
        return "sem agenda"
    local = dt.astimezone(_TZ) if dt.tzinfo else dt.replace(tzinfo=_TZ)
    hoje = datetime.now(tz=_TZ).date()
    delta = (local.date() - hoje).days
    hora = f"{local.hour:02d}h"
    if delta == 0:
        return f"hoje {hora}"
    if delta == 1:
        return f"amanhã {hora}"
    return f"{local.day:02d}/{local.month:02d} {hora}"


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def format_os_block(os_: _OsLike, cliente: _ClienteLike | None) -> str:
    status_key = _status_str(os_.status)
    emoji = STATUS_EMOJI.get(status_key, "🔵")
    nome = (cliente.nome if cliente and cliente.nome else None) or "Cliente sem nome"
    telefone = format_br_phone(cliente.whatsapp) if cliente and cliente.whatsapp else ""
    linha_cliente = f"👤 {nome}"
    if telefone:
        linha_cliente += f" — 📞 {telefone}"
    problema = _truncate(os_.problema or "", _MAX_PROBLEMA_LEN)
    return (
        f"*{os_.codigo}* {emoji} {status_key.replace('_', ' ')}\n"
        f"{linha_cliente}\n"
        f"📍 {os_.endereco}\n"
        f"🔧 {problema}\n"
        f"📅 {format_agendamento(os_.agendamento_at)}"
    )


def format_resumo(
    *,
    counts: dict[str, int],
    proxima: _OsLike | None,
) -> str:
    """Formata RESUMO. counts deve ter chaves: pendente, em_andamento, concluida_mes."""
    p = counts.get("pendente", 0)
    a = counts.get("em_andamento", 0)
    c = counts.get("concluida_mes", 0)
    if p == 0 and a == 0 and c == 0:
        return RESUMO_VAZIO_TEXT
    linhas = [
        "*Seu resumo*",
        "",
        f"🟡 Pendentes: {p}",
        f"🟠 Em andamento: {a}",
        f"✅ Concluídas (mês): {c}",
    ]
    if proxima is not None:
        linhas.append("")
        linhas.append(
            f"📅 Próxima agendada: {proxima.codigo} — {format_agendamento(proxima.agendamento_at)}"
        )
    return "\n".join(linhas)
```

- [ ] **Step 6.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound_formatters.py -v`
Expected: PASS (~14 tests)

- [ ] **Step 6.5: Commit**

```bash
git add apps/api/src/ondeline_api/services/tecnico_inbound.py apps/api/tests/test_tecnico_inbound_formatters.py
git commit -m "feat(tecnico-inbound): formatadores puros (os_block, resumo, agendamento)"
```

---

## Task 7: Dispatcher `handle_tecnico_message` + comandos OS/RESUMO/AJUDA

**Files:**
- Modify: `apps/api/src/ondeline_api/services/tecnico_inbound.py`
- Create: `apps/api/tests/test_tecnico_inbound.py`

- [ ] **Step 7.1: Write the failing tests**

Create `apps/api/tests/test_tecnico_inbound.py`:

```python
"""Dispatcher de comandos de técnico — testes com fakes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    OsStatus,
    Tecnico,
)
from ondeline_api.services.tecnico_inbound import (
    TecnicoInboundDeps,
    handle_tecnico_message,
)
from ondeline_api.webhook.parser import InboundEvent, InboundKind

pytestmark = pytest.mark.asyncio


# ── Fakes ────────────────────────────────────────────────────


@dataclass
class _FakeOsRow:
    codigo: str
    status: OsStatus
    problema: str
    endereco: str
    agendamento_at: datetime | None = None
    cliente_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    tecnico_id: UUID | None = None


@dataclass
class _FakeCliente:
    nome: str | None
    whatsapp: str | None
    id: UUID = field(default_factory=uuid4)


@dataclass
class _FakeOsRepo:
    ativas: list[_FakeOsRow] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=lambda: {"pendente": 0, "em_andamento": 0, "concluida_mes": 0})
    proxima: _FakeOsRow | None = None

    async def list_ativas_by_tecnico(self, tecnico_id, *, limit: int = 11):
        return self.ativas[:limit]

    async def count_by_status_for_tecnico(self, tecnico_id):
        return self.counts

    async def proxima_agendada(self, tecnico_id):
        return self.proxima


@dataclass
class _FakeClienteRepo:
    by_id: dict[UUID, _FakeCliente] = field(default_factory=dict)

    async def get_by_id(self, cliente_id: UUID):
        return self.by_id.get(cliente_id)


@dataclass
class _FakeOutbound:
    sent: list[tuple[str, str, UUID]] = field(default_factory=list)
    followups: list[tuple[UUID, str, str]] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self.sent.append((jid, text, conversa_id))

    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None:
        self.followups.append((conversa_id, resultado, resposta))

    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        pass


def _tecnico(whatsapp: str = "5597984109856") -> Tecnico:
    return Tecnico(id=uuid4(), nome="Téc", whatsapp=whatsapp, ativo=True)


def _conversa(jid: str = "5597984109856@s") -> Conversa:
    return Conversa(
        id=uuid4(), whatsapp=jid,
        estado=ConversaEstado.INICIO, status=ConversaStatus.BOT,
    )


def _evt(text: str, jid: str = "5597984109856@s") -> InboundEvent:
    return InboundEvent(
        external_id=f"E-{uuid4().hex[:8]}", jid=jid, push_name="Téc",
        kind=InboundKind.TEXT, text=text, from_me=False,
    )


def _deps(os_repo=None, cli_repo=None, outbound=None) -> TecnicoInboundDeps:
    return TecnicoInboundDeps(
        os_repo=os_repo or _FakeOsRepo(),
        cliente_repo=cli_repo or _FakeClienteRepo(),
        outbound=outbound or _FakeOutbound(),
        session=None,  # CONCLUIR (que precisa de session) testado na Task 8
    )


# ── Tests ─────────────────────────────────────────────────────


async def test_dispatch_ajuda_responds() -> None:
    out = _FakeOutbound()
    deps = _deps(outbound=out)
    consumed = await handle_tecnico_message(_evt("AJUDA"), _tecnico(), _conversa(), deps)
    assert consumed is True
    assert len(out.sent) == 1
    assert "Comandos disponíveis" in out.sent[0][1]


@pytest.mark.parametrize("text", ["AJUDA", "ajuda", "MENU", "Menu", "HELP", "?"])
async def test_dispatch_ajuda_aliases(text: str) -> None:
    out = _FakeOutbound()
    deps = _deps(outbound=out)
    consumed = await handle_tecnico_message(_evt(text), _tecnico(), _conversa(), deps)
    assert consumed is True
    assert "Comandos disponíveis" in out.sent[0][1]


async def test_dispatch_os_lists_active() -> None:
    cli = _FakeCliente(nome="João", whatsapp="5597912345678")
    os_repo = _FakeOsRepo(ativas=[
        _FakeOsRow(codigo="OS-1", status=OsStatus.PENDENTE, problema="p", endereco="e", cliente_id=cli.id),
        _FakeOsRow(codigo="OS-2", status=OsStatus.EM_ANDAMENTO, problema="q", endereco="f", cliente_id=cli.id),
    ])
    cli_repo = _FakeClienteRepo(by_id={cli.id: cli})
    out = _FakeOutbound()
    deps = _deps(os_repo=os_repo, cli_repo=cli_repo, outbound=out)

    consumed = await handle_tecnico_message(_evt("OS"), _tecnico(), _conversa(), deps)
    assert consumed is True
    assert len(out.sent) == 1
    text = out.sent[0][1]
    assert "Suas OS ativas (2)" in text
    assert "OS-1" in text and "OS-2" in text
    assert "João" in text


async def test_dispatch_os_empty() -> None:
    out = _FakeOutbound()
    deps = _deps(os_repo=_FakeOsRepo(ativas=[]), outbound=out)
    consumed = await handle_tecnico_message(_evt("OS"), _tecnico(), _conversa(), deps)
    assert consumed is True
    assert "não tem OS ativas" in out.sent[0][1]


async def test_dispatch_os_truncates_at_10() -> None:
    cli = _FakeCliente(nome="N", whatsapp=None)
    ativas = [
        _FakeOsRow(codigo=f"OS-{i:02d}", status=OsStatus.PENDENTE, problema="p", endereco="e", cliente_id=cli.id)
        for i in range(11)  # repo retorna 11 (limit+1)
    ]
    os_repo = _FakeOsRepo(ativas=ativas)
    cli_repo = _FakeClienteRepo(by_id={cli.id: cli})
    out = _FakeOutbound()
    deps = _deps(os_repo=os_repo, cli_repo=cli_repo, outbound=out)

    consumed = await handle_tecnico_message(_evt("OS"), _tecnico(), _conversa(), deps)
    assert consumed is True
    text = out.sent[0][1]
    assert "mostrando 10" in text  # mensagem de truncamento
    # OS-00 a OS-09 presentes; OS-10 não
    for i in range(10):
        assert f"OS-{i:02d}" in text
    assert "OS-10" not in text


async def test_dispatch_resumo() -> None:
    os_repo = _FakeOsRepo(counts={"pendente": 5, "em_andamento": 2, "concluida_mes": 28})
    out = _FakeOutbound()
    deps = _deps(os_repo=os_repo, outbound=out)

    consumed = await handle_tecnico_message(_evt("RESUMO"), _tecnico(), _conversa(), deps)
    assert consumed is True
    text = out.sent[0][1]
    assert "Pendentes: 5" in text
    assert "Em andamento: 2" in text
    assert "Concluídas (mês): 28" in text


async def test_dispatch_resumo_sem_proxima_omits_line() -> None:
    os_repo = _FakeOsRepo(counts={"pendente": 1, "em_andamento": 0, "concluida_mes": 0})
    out = _FakeOutbound()
    deps = _deps(os_repo=os_repo, outbound=out)
    await handle_tecnico_message(_evt("RESUMO"), _tecnico(), _conversa(), deps)
    assert "Próxima agendada" not in out.sent[0][1]


async def test_dispatch_resumo_vazio() -> None:
    out = _FakeOutbound()
    deps = _deps(outbound=out)  # counts default = todos zero
    await handle_tecnico_message(_evt("RESUMO"), _tecnico(), _conversa(), deps)
    assert "ainda não tem OS atribuídas" in out.sent[0][1]


async def test_dispatch_no_match_returns_false() -> None:
    out = _FakeOutbound()
    deps = _deps(outbound=out)
    consumed = await handle_tecnico_message(_evt("valeu cara"), _tecnico(), _conversa(), deps)
    assert consumed is False
    assert out.sent == []


@pytest.mark.parametrize("text", ["os lista", "OS pendente", "show OS", "RESUMOX"])
async def test_dispatch_partial_match_returns_false(text: str) -> None:
    out = _FakeOutbound()
    deps = _deps(outbound=out)
    consumed = await handle_tecnico_message(_evt(text), _tecnico(), _conversa(), deps)
    assert consumed is False
    assert out.sent == []
```

- [ ] **Step 7.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound.py -v`
Expected: FAIL with `ImportError: cannot import name 'TecnicoInboundDeps' from 'ondeline_api.services.tecnico_inbound'`

- [ ] **Step 7.3: Implement dispatcher e handlers**

Append em `apps/api/src/ondeline_api/services/tecnico_inbound.py`:

```python
# ── Dispatcher ────────────────────────────────────────────────────

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from ondeline_api.db.models.business import Conversa
from ondeline_api.webhook.parser import InboundEvent

log = structlog.get_logger(__name__)


_RE_OS = re.compile(r"^OS$", re.IGNORECASE)
_RE_RESUMO = re.compile(r"^RESUMOS?$", re.IGNORECASE)
_RE_AJUDA = re.compile(r"^(AJUDA|MENU|HELP|\?)$", re.IGNORECASE)
_RE_CONCLUIR = re.compile(r"^CONCLU[IÍ]R\s+(OS-[\w-]+)$", re.IGNORECASE)


class _OsRepoProto(Protocol):
    async def list_ativas_by_tecnico(self, tecnico_id: UUID, *, limit: int = 11) -> list[Any]: ...
    async def count_by_status_for_tecnico(self, tecnico_id: UUID) -> dict[str, int]: ...
    async def proxima_agendada(self, tecnico_id: UUID) -> Any | None: ...


class _ClienteRepoProto(Protocol):
    async def get_by_id(self, cliente_id: UUID) -> Any | None: ...


class _OutboundProto(Protocol):
    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None: ...
    def enqueue_followup_os(self, conversa_id: UUID, resultado: str, resposta: str) -> None: ...
    def enqueue_llm_turn(self, conversa_id: UUID) -> None: ...


@dataclass
class TecnicoInboundDeps:
    os_repo: _OsRepoProto
    cliente_repo: _ClienteRepoProto
    outbound: _OutboundProto
    session: Any = None  # AsyncSession — necessária para CONCLUIR (CHECKLIST_OS state)


async def handle_tecnico_message(
    evt: InboundEvent,
    tecnico: Any,  # Tecnico
    conversa: Conversa,
    deps: TecnicoInboundDeps,
) -> bool:
    """Despacha comando de técnico. Retorna True se consumiu a mensagem."""
    text = (evt.text or "").strip()
    if not text:
        return False

    # Ordem: CONCLUIR (mais específico) → OS → RESUMO → AJUDA
    m_conc = _RE_CONCLUIR.match(text)
    if m_conc:
        from ondeline_api.services.tecnico_inbound_concluir import handle_concluir
        return await handle_concluir(evt, tecnico, conversa, deps, codigo=m_conc.group(1).upper())

    if _RE_OS.match(text):
        await _cmd_os(evt, tecnico, conversa, deps)
        return True
    if _RE_RESUMO.match(text):
        await _cmd_resumo(evt, tecnico, conversa, deps)
        return True
    if _RE_AJUDA.match(text):
        await _cmd_ajuda(evt, conversa, deps)
        return True

    log.info("tecnico.cmd.no_match", tecnico_id=str(tecnico.id), text_len=len(text))
    return False


async def _cmd_ajuda(evt: InboundEvent, conversa: Conversa, deps: TecnicoInboundDeps) -> None:
    log.info("tecnico.cmd.identified", comando="AJUDA")
    deps.outbound.enqueue_send_outbound(evt.jid, AJUDA_TEXT, conversa.id)


async def _cmd_os(
    evt: InboundEvent, tecnico: Any, conversa: Conversa, deps: TecnicoInboundDeps
) -> None:
    log.info("tecnico.cmd.identified", comando="OS", tecnico_id=str(tecnico.id))
    rows = await deps.os_repo.list_ativas_by_tecnico(tecnico.id, limit=_OS_LIMIT + 1)
    if not rows:
        deps.outbound.enqueue_send_outbound(evt.jid, NO_OS_TEXT, conversa.id)
        return
    truncated = len(rows) > _OS_LIMIT
    to_show = rows[:_OS_LIMIT]

    # Resolve clientes
    blocks: list[str] = []
    for o in to_show:
        cli = await deps.cliente_repo.get_by_id(o.cliente_id) if o.cliente_id else None
        cli_view = _decrypt_cliente_view(cli)
        blocks.append(format_os_block(o, cli_view))

    header = f"*Suas OS ativas ({len(to_show)}):*\n"
    body = "\n\n".join(blocks)
    text = header + "\n" + body
    if truncated:
        text += f"\n\n_... mostrando {_OS_LIMIT}. Acesse o painel para ver todas._"
    deps.outbound.enqueue_send_outbound(evt.jid, text, conversa.id)


async def _cmd_resumo(
    evt: InboundEvent, tecnico: Any, conversa: Conversa, deps: TecnicoInboundDeps
) -> None:
    log.info("tecnico.cmd.identified", comando="RESUMO", tecnico_id=str(tecnico.id))
    counts = await deps.os_repo.count_by_status_for_tecnico(tecnico.id)
    proxima = await deps.os_repo.proxima_agendada(tecnico.id)
    text = format_resumo(counts=counts, proxima=proxima)
    deps.outbound.enqueue_send_outbound(evt.jid, text, conversa.id)


@dataclass
class _ClienteView:
    """Snapshot descriptografado de Cliente para uso em formatadores."""
    nome: str | None
    whatsapp: str | None


def _decrypt_cliente_view(cli: Any | None) -> _ClienteView | None:
    if cli is None:
        return None
    from ondeline_api.db.crypto import decrypt_pii

    nome = None
    if getattr(cli, "nome_encrypted", None):
        try:
            nome = decrypt_pii(cli.nome_encrypted)
        except Exception:  # pragma: no cover — defensivo
            nome = None
    whatsapp = getattr(cli, "whatsapp", None)
    return _ClienteView(nome=nome, whatsapp=whatsapp)
```

Atualizar `_FakeClienteRepo` no teste para retornar diretamente algo que parece com `_ClienteView` (sem `nome_encrypted`). Para isso, o `_decrypt_cliente_view` precisa tolerar input que já tem `.nome` (e.g. dataclass com `nome`). Ajustar `_decrypt_cliente_view`:

```python
def _decrypt_cliente_view(cli: Any | None) -> _ClienteView | None:
    if cli is None:
        return None
    # Atalho para testes/fakes que já têm .nome em claro
    if hasattr(cli, "nome") and not hasattr(cli, "nome_encrypted"):
        return _ClienteView(nome=cli.nome, whatsapp=getattr(cli, "whatsapp", None))

    from ondeline_api.db.crypto import decrypt_pii

    nome = None
    if getattr(cli, "nome_encrypted", None):
        try:
            nome = decrypt_pii(cli.nome_encrypted)
        except Exception:  # pragma: no cover
            nome = None
    return _ClienteView(nome=nome, whatsapp=getattr(cli, "whatsapp", None))
```

- [ ] **Step 7.4: Add stub `handle_concluir` for import**

Para os testes desta task funcionarem sem precisar do CONCLUIR ainda, crie um stub mínimo:

Create `apps/api/src/ondeline_api/services/tecnico_inbound_concluir.py`:

```python
"""Handler CONCLUIR — preenchido na Task 8."""
from __future__ import annotations

from typing import Any

from ondeline_api.db.models.business import Conversa
from ondeline_api.webhook.parser import InboundEvent


async def handle_concluir(
    evt: InboundEvent,
    tecnico: Any,
    conversa: Conversa,
    deps: Any,
    *,
    codigo: str,
) -> bool:
    raise NotImplementedError("preenchido na Task 8")
```

- [ ] **Step 7.5: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound.py -v`
Expected: PASS (todos os testes — ~12 incluindo parametrizados)

- [ ] **Step 7.6: Commit**

```bash
git add apps/api/src/ondeline_api/services/tecnico_inbound.py \
        apps/api/src/ondeline_api/services/tecnico_inbound_concluir.py \
        apps/api/tests/test_tecnico_inbound.py
git commit -m "feat(tecnico-inbound): dispatcher + handlers OS/RESUMO/AJUDA"
```

---

## Task 8: Migrar handler `CONCLUIR` para `tecnico_inbound_concluir`

**Files:**
- Modify: `apps/api/src/ondeline_api/services/tecnico_inbound_concluir.py` (preencher stub)
- Create: `apps/api/tests/test_tecnico_inbound_concluir.py`

- [ ] **Step 8.1: Write the failing tests**

Create `apps/api/tests/test_tecnico_inbound_concluir.py`:

```python
"""Handler CONCLUIR migrado do inbound.py."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    OrdemServico,
    OsStatus,
    Tecnico,
)
from ondeline_api.services.tecnico_inbound import TecnicoInboundDeps
from ondeline_api.services.tecnico_inbound_concluir import handle_concluir
from ondeline_api.webhook.parser import InboundEvent, InboundKind

pytestmark = pytest.mark.asyncio


@dataclass
class _FakeOutbound:
    sent: list[tuple[str, str, UUID]] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self.sent.append((jid, text, conversa_id))

    def enqueue_followup_os(self, *a, **kw) -> None: pass
    def enqueue_llm_turn(self, *a, **kw) -> None: pass


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._v = value

    def scalar_one_or_none(self) -> Any:
        return self._v


class _FakeSession:
    """Session falsa que devolve o próximo valor de uma fila para cada execute()."""

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.flushes = 0

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        if not self._results:
            return _FakeScalarResult(None)
        return _FakeScalarResult(self._results.pop(0))

    async def flush(self) -> None:
        self.flushes += 1


def _tec() -> Tecnico:
    return Tecnico(id=uuid4(), nome="T", whatsapp="5597984109856", ativo=True)


def _conv() -> Conversa:
    return Conversa(
        id=uuid4(), whatsapp="5597984109856@s",
        estado=ConversaEstado.INICIO, status=ConversaStatus.BOT,
    )


def _evt(text: str = "CONCLUIR OS-1234") -> InboundEvent:
    return InboundEvent(
        external_id="E1", jid="5597984109856@s", push_name="T",
        kind=InboundKind.TEXT, text=text, from_me=False,
    )


def _os(codigo: str = "OS-1234", tecnico_id: UUID | None = None, status: OsStatus = OsStatus.PENDENTE) -> OrdemServico:
    return OrdemServico(
        id=uuid4(), codigo=codigo, cliente_id=uuid4(),
        tecnico_id=tecnico_id, status=status,
        problema="p", endereco="e",
    )


async def test_concluir_inicia_checklist() -> None:
    tec = _tec()
    conv = _conv()
    os_ = _os(tecnico_id=tec.id)
    session = _FakeSession([os_])
    out = _FakeOutbound()
    deps = TecnicoInboundDeps(os_repo=None, cliente_repo=None, outbound=out, session=session)

    consumed = await handle_concluir(_evt(), tec, conv, deps, codigo="OS-1234")
    assert consumed is True
    assert conv.estado is ConversaEstado.CHECKLIST_OS
    assert conv.checklist_metadata == {
        "os_id": str(os_.id),
        "os_codigo": "OS-1234",
        "step": 1,
        "respostas": {},
    }
    assert len(out.sent) == 1
    assert "OS *OS-1234*" in out.sent[0][1] or "OS-1234" in out.sent[0][1]
    assert "1️⃣" in out.sent[0][1]


async def test_concluir_os_nao_encontrada() -> None:
    tec = _tec()
    conv = _conv()
    session = _FakeSession([None])  # OS query devolve None
    out = _FakeOutbound()
    deps = TecnicoInboundDeps(os_repo=None, cliente_repo=None, outbound=out, session=session)

    consumed = await handle_concluir(_evt(), tec, conv, deps, codigo="OS-9999")
    assert consumed is True
    assert "OS-9999" in out.sent[0][1]
    assert "não encontrada" in out.sent[0][1] or "ja concluida" in out.sent[0][1].lower()
    assert conv.estado is ConversaEstado.INICIO  # não muda


async def test_concluir_os_de_outro_tecnico() -> None:
    tec = _tec()
    outro_tec_id = uuid4()
    conv = _conv()
    os_ = _os(tecnico_id=outro_tec_id)
    session = _FakeSession([os_])
    out = _FakeOutbound()
    deps = TecnicoInboundDeps(os_repo=None, cliente_repo=None, outbound=out, session=session)

    consumed = await handle_concluir(_evt(), tec, conv, deps, codigo="OS-1234")
    assert consumed is True
    assert "não está atribuída a você" in out.sent[0][1]
    assert conv.estado is ConversaEstado.INICIO
```

- [ ] **Step 8.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound_concluir.py -v`
Expected: FAIL com `NotImplementedError: preenchido na Task 8`

- [ ] **Step 8.3: Implement `handle_concluir`**

Replace conteúdo de `apps/api/src/ondeline_api/services/tecnico_inbound_concluir.py`:

```python
"""Handler do comando CONCLUIR OS-XXXX.

Inicia o checklist de 3 passos na conversa do técnico (mesmo fluxo
anteriormente embutido em services/inbound.py).
"""
from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    OrdemServico,
    OsStatus,
)
from ondeline_api.webhook.parser import InboundEvent

log = structlog.get_logger(__name__)


async def handle_concluir(
    evt: InboundEvent,
    tecnico: Any,
    conversa: Conversa,
    deps: Any,  # TecnicoInboundDeps — Any para evitar circular import
    *,
    codigo: str,
) -> bool:
    """Inicia checklist da OS especificada. Retorna True (sempre consome)."""
    log.info("tecnico.cmd.identified", comando="CONCLUIR", codigo=codigo, tecnico_id=str(tecnico.id))

    session = deps.session
    os_row = (
        await session.execute(
            select(OrdemServico).where(
                OrdemServico.codigo == codigo,
                OrdemServico.status.in_([OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]),
            )
        )
    ).scalar_one_or_none()

    if os_row is None:
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            f"OS {codigo} não encontrada ou já concluída. Verifique o código e tente novamente.",
            conversa.id,
        )
        return True

    if os_row.tecnico_id != tecnico.id:
        deps.outbound.enqueue_send_outbound(
            evt.jid,
            f"A OS {codigo} não está atribuída a você.",
            conversa.id,
        )
        return True

    conversa.checklist_metadata = {
        "os_id": str(os_row.id),
        "os_codigo": codigo,
        "step": 1,
        "respostas": {},
    }
    conversa.estado = ConversaEstado.CHECKLIST_OS
    conversa.status = ConversaStatus.BOT

    deps.outbound.enqueue_send_outbound(
        evt.jid,
        f"✅ OS *{codigo}* encontrada! Vamos registrar a conclusão em 3 passos.\n\n"
        "1️⃣ *O que foi feito?* Descreva o serviço realizado.",
        conversa.id,
    )
    return True
```

- [ ] **Step 8.4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/test_tecnico_inbound_concluir.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8.5: Commit**

```bash
git add apps/api/src/ondeline_api/services/tecnico_inbound_concluir.py \
        apps/api/tests/test_tecnico_inbound_concluir.py
git commit -m "feat(tecnico-inbound): migrar handler CONCLUIR pro modulo novo"
```

---

## Task 9: Integrar dispatcher no `inbound.py`

**Files:**
- Modify: `apps/api/src/ondeline_api/services/inbound.py`
- Create: `apps/api/tests/test_inbound_tecnico_routing.py`

Esta task remove o bloco CONCLUIR inline antigo de `inbound.py`, remove o `_br_local_digits` local (usa o de `services/phone.py`), e adiciona a chamada ao novo dispatcher.

- [ ] **Step 9.1: Write the failing integration tests**

Create `apps/api/tests/test_inbound_tecnico_routing.py`:

```python
"""Integração inbound + dispatcher de técnico.

Verifica:
1. Mensagem de técnico bypassa o gate bot.ativo
2. Mensagem de cliente continua sendo silenciada com bot inativo (regressão)
3. CHECKLIST_OS tem precedência sobre dispatcher de técnico
4. JID cadastrado como cliente E técnico: técnico vence
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
    OsStatus,
    Tecnico,
)
from ondeline_api.services.inbound import InboundDeps, process_inbound_message
from ondeline_api.webhook.parser import InboundEvent, InboundKind

pytestmark = pytest.mark.asyncio


# ── Fakes mínimas (reuso do padrão de test_inbound_service.py) ──────


class FakeConversaRepo:
    def __init__(self, conv: Conversa | None = None) -> None:
        self.by_jid: dict[str, Conversa] = {conv.whatsapp: conv} if conv else {}

    async def get_or_create_by_whatsapp(self, whatsapp: str) -> Conversa:
        if whatsapp in self.by_jid:
            return self.by_jid[whatsapp]
        c = Conversa(
            id=uuid4(), whatsapp=whatsapp,
            estado=ConversaEstado.INICIO, status=ConversaStatus.BOT,
        )
        self.by_jid[whatsapp] = c
        return c

    async def update_estado_status(self, conversa, *, estado, status) -> None:
        conversa.estado = estado
        conversa.status = status

    async def set_cliente(self, conversa, cliente_id) -> None:
        conversa.cliente_id = cliente_id

    async def add_tag(self, conversa, tag) -> None:
        pass


class FakeMensagemRepo:
    def __init__(self) -> None:
        self.inserted: list[Mensagem] = []

    async def insert_inbound_or_skip(self, *, conversa_id, external_id, text, media_type, media_url):
        m = Mensagem(
            id=uuid4(), conversa_id=conversa_id, external_id=external_id,
            role=MensagemRole.CLIENTE, content_encrypted=text,
            media_type=media_type, media_url=media_url,
        )
        self.inserted.append(m)
        return m

    async def insert_bot_reply(self, *, conversa_id, text):
        pass


@dataclass
class FakeOutboundQueue:
    sent: list[tuple[str, str, UUID]] = field(default_factory=list)
    llm_turns: list[UUID] = field(default_factory=list)

    def enqueue_send_outbound(self, jid, text, conversa_id) -> None:
        self.sent.append((jid, text, conversa_id))

    def enqueue_llm_turn(self, conversa_id) -> None:
        self.llm_turns.append(conversa_id)

    def enqueue_followup_os(self, *a, **kw) -> None:
        pass


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._v = value

    def scalar_one_or_none(self): return self._v
    def scalars(self): return self
    def all(self): return self._v if isinstance(self._v, list) else [self._v]


class FakeSession:
    """Session falsa que devolve a lista de resultados em sequência.

    Cada chamada `execute(stmt)` consome o próximo resultado da fila.
    Usar para configurar respostas determinísticas a queries específicas.
    """

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)

    async def execute(self, stmt):
        if self._results:
            return _FakeScalarResult(self._results.pop(0))
        return _FakeScalarResult(None)

    async def flush(self): pass


def _evt(text: str, jid: str = "5597984109856@s") -> InboundEvent:
    return InboundEvent(
        external_id=f"E-{uuid4().hex[:8]}", jid=jid, push_name="T",
        kind=InboundKind.TEXT, text=text, from_me=False,
    )


async def test_tecnico_msg_bypassa_bot_inativo() -> None:
    """bot.ativo=False; técnico envia AJUDA → deve receber resposta."""
    tec = Tecnico(id=uuid4(), nome="T", whatsapp="5597984109856", ativo=True)
    out = FakeOutboundQueue()
    # Fila de execute(): [bot.ativo=False (não usado pois técnico retorna antes),
    #                    list-tecnicos com 1 técnico]
    # Na verdade a ordem real é: lookup técnico ANTES de bot.ativo.
    # FakeSession devolve por ordem de chamada.
    session = FakeSession([[tec]])  # primeiro execute = list técnicos
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=out,
        ack_text="ACK",
        session=session,
    )

    result = await process_inbound_message(_evt("AJUDA"), deps)
    assert result.persisted is True
    assert len(out.sent) == 1
    assert "Comandos disponíveis" in out.sent[0][1]


async def test_cliente_msg_quando_bot_inativo_silenciado() -> None:
    """REGRESSÃO: cliente comum com bot.ativo=False → silêncio."""
    out = FakeOutboundQueue()
    # execute() #1: list técnicos (vazio — JID não casa)
    # execute() #2: bot.ativo lookup retorna False
    session = FakeSession([[], False])
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=out,
        ack_text="ACK",
        session=session,
    )

    result = await process_inbound_message(_evt("oi", jid="5511999@s"), deps)
    assert result.skipped_reason == "bot_desativado"
    assert out.sent == []


async def test_tecnico_em_checklist_responde_passo_nao_comando() -> None:
    """Técnico em CHECKLIST_OS step=1: 'OS' é descrição do serviço, não comando."""
    tec = Tecnico(id=uuid4(), nome="T", whatsapp="5597984109856", ativo=True)
    conv = Conversa(
        id=uuid4(), whatsapp="5597984109856@s",
        estado=ConversaEstado.CHECKLIST_OS, status=ConversaStatus.BOT,
        checklist_metadata={"os_id": str(uuid4()), "os_codigo": "OS-X", "step": 1, "respostas": {}},
    )
    out = FakeOutboundQueue()
    session = FakeSession([])  # checklist não usa session pra essa rota (só salva via repos)
    deps = InboundDeps(
        conversas=FakeConversaRepo(conv=conv),
        mensagens=FakeMensagemRepo(),
        outbound=out,
        ack_text="ACK",
        session=session,
    )

    result = await process_inbound_message(_evt("OS"), deps)
    assert result.persisted is True
    # O bot deve ter avançado o checklist (passo 2) — não enviou lista de OS
    assert any("SIM" in msg or "NÃO" in msg for _, msg, _ in out.sent)
    assert not any("Suas OS ativas" in msg for _, msg, _ in out.sent)


async def test_tecnico_no_match_silent() -> None:
    """Técnico manda texto livre → consumed=True, zero outbound, skipped_reason set."""
    tec = Tecnico(id=uuid4(), nome="T", whatsapp="5597984109856", ativo=True)
    out = FakeOutboundQueue()
    session = FakeSession([[tec]])
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=FakeMensagemRepo(),
        outbound=out,
        ack_text="ACK",
        session=session,
    )

    result = await process_inbound_message(_evt("valeu cara"), deps)
    assert result.persisted is True
    assert result.skipped_reason == "tecnico_no_command"
    assert out.sent == []
    assert out.llm_turns == []  # NÃO enfileirou LLM
```

- [ ] **Step 9.2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/test_inbound_tecnico_routing.py -v`
Expected: pelo menos 1 falha — `test_tecnico_no_match_silent` espera comportamento novo que ainda não existe (hoje cai no FSM/LLM).

- [ ] **Step 9.3: Refactor `inbound.py`**

Edit `apps/api/src/ondeline_api/services/inbound.py`:

**3a. Remover `_br_local_digits` local (linhas 106-120).** Adicionar no topo dos imports:

```python
from ondeline_api.services.phone import br_local_digits
from ondeline_api.services.tecnico_inbound import TecnicoInboundDeps, handle_tecnico_message
from ondeline_api.repositories.tecnico import TecnicoRepo
```

E remover a função `_br_local_digits` definida em `inbound.py`.

**3b. Remover o bloco CONCLUIR antigo (linhas ~160-249).** Todo o bloco que começa em:

```python
    # Detecção de comando CONCLUIR OS-* (técnico finaliza OS via WhatsApp).
    if (
        evt.kind is InboundKind.TEXT
        ...
```

e termina em:

```python
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False
                )
```

Substituir por nada (será movido para baixo do CHECKLIST_OS, ver 3c).

**3c. Adicionar bloco novo APÓS CHECKLIST_OS e ANTES de `bot_ativo`** (após linha ~353). Inserir:

```python
    # Dispatcher de técnico — identifica pelo JID e responde comandos OS/RESUMO/AJUDA/CONCLUIR.
    # Roda ANTES de bot.ativo para que técnico sempre passe mesmo com bot desligado.
    # Texto de técnico que não casa nenhum comando é IGNORADO silenciosamente (não cai no fluxo cliente).
    if (
        deps.session is not None
        and evt.kind is InboundKind.TEXT
        and evt.text
    ):
        tecnico_sender = await TecnicoRepo(deps.session).get_by_jid(evt.jid)
        if tecnico_sender is not None:
            from ondeline_api.repositories.cliente import ClienteRepo
            from ondeline_api.repositories.ordem_servico import OrdemServicoRepo

            tec_deps = TecnicoInboundDeps(
                os_repo=OrdemServicoRepo(deps.session),
                cliente_repo=ClienteRepo(deps.session),
                outbound=deps.outbound,
                session=deps.session,
            )
            consumed = await handle_tecnico_message(evt, tecnico_sender, conversa, tec_deps)
            if consumed:
                return InboundResult(
                    conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False,
                )
            return InboundResult(
                conversa_id=conversa.id, persisted=True, duplicate=False, escalated=False,
                skipped_reason="tecnico_no_command",
            )
```

**3d. Verificar:** `ClienteRepo` precisa de `get_by_id`. Conferir:

Run: `grep -n "get_by_id\|async def" apps/api/src/ondeline_api/repositories/cliente.py | head -10`
Se `get_by_id` não existir, adicionar (segue padrão dos outros repos):

```python
    async def get_by_id(self, cliente_id: UUID) -> Cliente | None:
        from sqlalchemy import select
        stmt = select(Cliente).where(Cliente.id == cliente_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()
```

- [ ] **Step 9.4: Run all related tests**

Run: `cd apps/api && uv run pytest tests/test_inbound_tecnico_routing.py tests/test_inbound_service.py tests/test_tecnico_inbound.py tests/test_tecnico_inbound_concluir.py -v`
Expected: PASS (todos)

- [ ] **Step 9.5: Run full test suite**

Run: `cd apps/api && uv run pytest -x`
Expected: PASS (todos os testes anteriores continuam verdes — sem regressões)

Se algum teste falhar, ler a falha e ajustar a integração (provavelmente algum teste assumia que o bloco CONCLUIR vivia em `inbound.py`).

- [ ] **Step 9.6: Commit**

```bash
git add apps/api/src/ondeline_api/services/inbound.py \
        apps/api/src/ondeline_api/repositories/cliente.py \
        apps/api/tests/test_inbound_tecnico_routing.py
git commit -m "refactor(inbound): integrar dispatcher de tecnico, remover blocos inline"
```

---

## Task 10: Smoke check + validação em produção

**Files:** nenhum (validação manual)

- [ ] **Step 10.1: Garantir suite full verde + lint/type**

```bash
cd apps/api
uv run pytest
uv run ruff check src tests
uv run mypy src
```

Expected: tudo verde.

- [ ] **Step 10.2: Commit final + push**

Se houver ajustes acumulados:
```bash
git status
# Se limpo, segue. Se sujo, commit com mensagem descritiva.
git push origin main
```

- [ ] **Step 10.3: Aguardar deploy via Watchtower**

Após push, o pipeline GHCR builda + Watchtower puxa em prod (ver `feedback_watchtower_deploy`). Acompanhar:

```bash
gh run watch
```

- [ ] **Step 10.4: Validar em produção com WhatsApp real**

Conectado via SSH na VM, abrir log:
```bash
ssh prod 'docker logs -f ondeline-api 2>&1 | grep tecnico.cmd'
```

No WhatsApp pessoal (cadastrado como técnico), enviar uma a uma:

1. `AJUDA` → conferir mensagem com comandos.
2. `OS` → conferir lista ou "Você não tem OS ativas".
3. `RESUMO` → conferir contagens.
4. `oi` → conferir **silêncio** (zero resposta).
5. `CONCLUIR OS-XXXX` (OS de teste real) → conferir início do checklist.

Logs esperados:
```
tecnico.cmd.identified comando=AJUDA
tecnico.cmd.identified comando=OS
tecnico.cmd.identified comando=RESUMO
tecnico.cmd.no_match text_len=2
tecnico.cmd.identified comando=CONCLUIR
```

- [ ] **Step 10.5: Documentar em memória**

Se tudo ok, criar memória `project_tecnico_commands.md` apontando para o spec/plan e listando os comandos suportados pra consultas futuras.

---

## Notas finais

- **Migration?** Nenhuma — schema não muda.
- **Frontend?** Nada (dashboard e PWA não são afetados; técnico ainda usa o PWA pra outros fluxos).
- **Worker Celery?** Apenas o handler CONCLUIR continua enfileirando follow-up via path existente (cliente, não técnico) — mudança transparente.
- **Performance:** lookup de técnico carrega TODOS os técnicos ativos em memória (mesmo padrão do código atual). Para >1000 técnicos, refatorar para query indexada por suffix; hoje (~10 técnicos) é trivial.
