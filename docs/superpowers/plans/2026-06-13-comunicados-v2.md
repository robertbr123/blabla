# Comunicados v2 — Implementação (sync templates, import CSV, botões, filtros dinâmicos)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o Comunicados para: filtros em dropdown (valores reais da base), templates sincronizados da Meta + cadastro manual (com botões), e disparo para listas importadas via CSV (inclusive contatos fora do cadastro).

**Architecture:** Estende o sistema v1. Templates ganham estrutura completa (variáveis+header+botões) preenchida por sync da Graph API (canais Cloud ativos) ou cadastro manual. Destinatários passam a aceitar contatos sem `cliente_id` (importados) com params próprios por contato; o sender mescla params do destinatário com os padrões da campanha. Telefones do CSV são normalizados pro formato Cloud.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, httpx (Graph API), csv (stdlib), Next.js + React Query.

---

## ⚠️ Convenções deste repo (ler antes)

- **Não rodar pytest/alembic/docker/uv localmente** — sem stack local; testes rodam no CI/deploy. Pode rodar `ruff check <arquivo>`/`mypy <arquivo>` SE disponível, senão pular.
- **Claude commita; PUSH é sempre do Robert.** Nunca `git push`.
- **Gotchas do CI já conhecidos (deste projeto):**
  - `ruff` é gate: sem imports não usados; import multi-linha que cabe em 1 linha é colapsado; `import X` vem antes de `from Y`, sem linha em branco entre third-party e first-party.
  - `mypy` strict + plugin pydantic: passar `dict`/`list[dict]` direto pra campo tipado de schema falha → usar `Model.model_validate(...)`. Dict literal com valores `str|None` passado a `dict[str, Any]` → anotar `var: dict[str, Any] = {...}`. Lib sem stubs → `[[tool.mypy.overrides]] ignore_missing_imports`.
  - **Banco de teste do CI roda as migrations** (seed presente) e é **compartilhado entre testes que commitam** → em teste, usar valores únicos (uuid4) pra dados com unique/contagem; não inserir linhas que o seed já cria.
- **Migration mais recente:** `0049_comunicados_broadcast`. A nova é `0050`.
- **Padrões a seguir** (confirmados no código): modelos em `db/models/business.py` (sem mixin; `created_at` inline); migrations com `postgresql.UUID(as_uuid=True)` PK sem server default, `postgresql.JSONB`; router em `api/v1/`, deps `require_role(Role.ADMIN)`/`get_db`; upload `file: Annotated[UploadFile, File()]` + `await file.read()`.

---

## Estrutura de arquivos

**Backend (`apps/api/src/ondeline_api/`)**
- `db/models/business.py` — **modificar**: `BroadcastTemplate.botoes`; `CampanhaDestinatario` (cliente_id nullable + body_params + button_param); `Campanha` (origem + button_param).
- `alembic/versions/0050_comunicados_v2.py` — **criar**.
- `services/phone.py` — **modificar**: `to_cloud_jid`.
- `services/segmento.py` — **modificar**: `valores_distintos`.
- `services/whatsapp_templates_sync.py` — **criar**: `parse_meta_template`, `sincronizar_templates`.
- `services/broadcast_sender.py` — **modificar**: params por destinatário + botão.
- `services/broadcast_import.py` — **criar**: `parse_csv_destinatarios`.
- `adapters/whatsapp/base.py` — **modificar**: `send_template` ganha `button_url_param`.
- `adapters/whatsapp/cloud.py` — **modificar**: `send_template` botão + `list_message_templates`.
- `adapters/whatsapp/evolution.py` — **modificar**: assinatura `send_template` (mantém NotImplementedError).
- `api/schemas/comunicado.py` — **modificar**: botões, origem, button_param, schemas de template manual/valores/import.
- `api/v1/comunicados.py` — **modificar**: novos endpoints + create_campanha.

**Frontend (`apps/dashboard/`)**
- `lib/api/types.ts`, `lib/api/queries.ts` — **modificar**.
- `components/comunicado-form.tsx` — **modificar**.
- `components/comunicado-templates.tsx` — **criar** (lista + sync + form manual).
- `app/(admin)/comunicados/templates/page.tsx` — **criar**.
- `components/comunicado-list.tsx` — **modificar**: link pra Templates.

**Testes (`apps/api/tests/`)**
- `test_phone_cloud_jid.py`, `test_segmento_valores.py`, `test_templates_sync.py`, `test_broadcast_import.py` — **criar**; `test_broadcast_task.py` — **modificar** (params por destinatário).

---

## FASE 1 — Modelos + migration

### Task 1: Mudanças nos modelos ORM

**Files:** Modify `apps/api/src/ondeline_api/db/models/business.py`

- [ ] **Step 1: Em `BroadcastTemplate`**, adicionar após `header_tipo`:

```python
    # [{"index": 0, "tipo": "url"|"quick_reply"|"phone", "texto": "...", "url_dinamica": false}]
    botoes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
```

- [ ] **Step 2: Em `Campanha`**, adicionar após `segmentacao`:

```python
    # segmento | importado
    origem: Mapped[str] = mapped_column(
        String(12), nullable=False, default="segmento", server_default="segmento"
    )
    # valor padrão do botão URL dinâmico (quando o template tiver)
    button_param: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 3: Em `CampanhaDestinatario`**, tornar `cliente_id` nullable e adicionar overrides. Trocar a linha do `cliente_id` por:

```python
    cliente_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=True
    )
```

E adicionar após `whatsapp`:

```python
    # override por contato (import CSV); None = usa o padrão da campanha
    body_params: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    button_param: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/business.py
git commit -m "feat(comunicados-v2): modelos (botoes, origem, params por destinatario, cliente_id nullable)"
```

---

### Task 2: Migration 0050

**Files:** Create `apps/api/alembic/versions/0050_comunicados_v2.py`

- [ ] **Step 1: Criar a migration**

```python
"""Comunicados v2: botoes em templates, origem/button_param em campanha,
params por destinatario, cliente_id nullable.

Revision ID: 0050_comunicados_v2
Revises: 0049_comunicados_broadcast
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_comunicados_v2"
down_revision: str | None = "0049_comunicados_broadcast"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "broadcast_templates",
        sa.Column("botoes", postgresql.JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "campanhas",
        sa.Column("origem", sa.String(12), nullable=False, server_default="segmento"),
    )
    op.add_column("campanhas", sa.Column("button_param", sa.Text(), nullable=True))
    op.add_column(
        "campanha_destinatarios",
        sa.Column("body_params", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "campanha_destinatarios", sa.Column("button_param", sa.Text(), nullable=True)
    )
    op.alter_column("campanha_destinatarios", "cliente_id", nullable=True)


def downgrade() -> None:
    op.alter_column("campanha_destinatarios", "cliente_id", nullable=False)
    op.drop_column("campanha_destinatarios", "button_param")
    op.drop_column("campanha_destinatarios", "body_params")
    op.drop_column("campanhas", "button_param")
    op.drop_column("campanhas", "origem")
    op.drop_column("broadcast_templates", "botoes")
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/alembic/versions/0050_comunicados_v2.py
git commit -m "feat(comunicados-v2): migration 0050"
```

---

## FASE 2 — Serviços backend

### Task 3: `to_cloud_jid` (TDD)

**Files:** Modify `apps/api/src/ondeline_api/services/phone.py`; Create `apps/api/tests/test_phone_cloud_jid.py`

- [ ] **Step 1: Teste**

```python
# apps/api/tests/test_phone_cloud_jid.py
from __future__ import annotations

from ondeline_api.services.phone import to_cloud_jid


def test_ja_normalizado_com_ddi() -> None:
    assert to_cloud_jid("5592999999999") == "5592999999999"


def test_com_pontuacao_adiciona_ddi() -> None:
    assert to_cloud_jid("(92) 99999-9999") == "5592999999999"


def test_ddd_mais_numero_sem_ddi() -> None:
    assert to_cloud_jid("92999999999") == "5592999999999"


def test_dez_digitos_fixo_like() -> None:
    assert to_cloud_jid("9233334444") == "559233334444"


def test_invalido_retorna_none() -> None:
    assert to_cloud_jid("999") is None
    assert to_cloud_jid("") is None
    assert to_cloud_jid(None) is None
    assert to_cloud_jid("abc") is None
```

- [ ] **Step 2: Rodar (CI) — FAIL** (`to_cloud_jid` não existe).

- [ ] **Step 3: Implementar** — adicionar ao fim de `services/phone.py` (o `_DIGITS_RE` já existe no topo do arquivo):

```python
def to_cloud_jid(raw: str | None) -> str | None:
    """Normaliza um telefone BR pro formato do WhatsApp Cloud: DDI 55 + DDD +
    número, só dígitos (E.164 sem '+'). Retorna None se não der pra formar um
    número BR plausível.
    """
    if not raw:
        return None
    d = _DIGITS_RE.sub("", raw)
    if not d:
        return None
    if d.startswith("55") and len(d) in (12, 13):
        return d
    if len(d) in (10, 11):
        return "55" + d
    return None
```

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/phone.py apps/api/tests/test_phone_cloud_jid.py
git commit -m "feat(comunicados-v2): to_cloud_jid (normaliza telefone p/ Cloud) + testes"
```

---

### Task 4: valores distintos do segmento (TDD)

**Files:** Modify `apps/api/src/ondeline_api/services/segmento.py`; Create `apps/api/tests/test_segmento_valores.py`

- [ ] **Step 1: Teste**

```python
# apps/api/tests/test_segmento_valores.py
from __future__ import annotations

import pytest

from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente
from ondeline_api.services.segmento import valores_distintos


async def _mk(session, *, cidade=None, status=None, plano=None, deleted=False):
    from uuid import uuid4

    c = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("0"),
        cpf_hash=hash_pii(uuid4().hex),
        nome_encrypted=encrypt_pii("x"),
        whatsapp="5592" + uuid4().hex[:8],
        cidade=cidade,
        status=status,
        plano=plano,
    )
    if deleted:
        from datetime import UTC, datetime

        c.deleted_at = datetime.now(tz=UTC)
    session.add(c)
    await session.flush()


@pytest.mark.asyncio
async def test_valores_distintos_ignora_nulos_e_deletados(db_session) -> None:
    marca = "ZZ" + __import__("uuid").uuid4().hex[:6]
    await _mk(db_session, cidade=f"Manaus{marca}", status=f"Ativo{marca}", plano=f"100MB{marca}")
    await _mk(db_session, cidade=f"Manaus{marca}", status=None, plano=None)
    await _mk(db_session, cidade=f"Del{marca}", status=f"X{marca}", deleted=True)

    out = await valores_distintos(db_session)

    assert f"Manaus{marca}" in out["cidades"]
    assert f"Del{marca}" not in out["cidades"]
    assert f"Ativo{marca}" in out["status"]
    assert f"100MB{marca}" in out["planos"]
    # sem duplicar
    assert out["cidades"].count(f"Manaus{marca}") == 1
```

- [ ] **Step 2: Rodar (CI) — FAIL**.

- [ ] **Step 3: Implementar** — adicionar a `services/segmento.py` (imports `select`, `Cliente`, `AsyncSession` já existem; `func` já importado):

```python
async def valores_distintos(session: AsyncSession) -> dict[str, list[str]]:
    """Valores distintos de cidade/status/plano na base (clientes vivos)."""
    out: dict[str, list[str]] = {}
    for chave, coluna in (
        ("cidades", Cliente.cidade),
        ("status", Cliente.status),
        ("planos", Cliente.plano),
    ):
        stmt = (
            select(coluna)
            .where(Cliente.deleted_at.is_(None), coluna.is_not(None), coluna != "")
            .distinct()
            .order_by(coluna)
        )
        out[chave] = [v for (v,) in (await session.execute(stmt)).all()]
    return out
```

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/segmento.py apps/api/tests/test_segmento_valores.py
git commit -m "feat(comunicados-v2): valores_distintos p/ filtros dropdown + testes"
```

---

### Task 5: Adapter — botão dinâmico + listar templates

**Files:** Modify `apps/api/src/ondeline_api/adapters/whatsapp/base.py`, `apps/api/src/ondeline_api/adapters/whatsapp/cloud.py`, `apps/api/src/ondeline_api/adapters/whatsapp/evolution.py`

- [ ] **Step 1: Em `base.py`**, no Protocol `WhatsAppAdapter`, atualizar a assinatura de `send_template` adicionando `button_url_param`:

```python
    async def send_template(
        self,
        jid: str,
        *,
        name: str,
        language: str = "pt_BR",
        body_params: list[str] | None = None,
        header_media_url: str | None = None,
        header_media_type: str | None = None,
        otp_code: str | None = None,
        button_url_param: str | None = None,
    ) -> SendResult: ...
```

- [ ] **Step 2: Em `cloud.py`**, atualizar a assinatura de `send_template` (adicionar `button_url_param: str | None = None,` após `otp_code`) e, logo após o bloco `if otp_code is not None:`, adicionar:

```python
        if button_url_param is not None:
            # Botão URL dinâmico (índice 0). Botão estático não precisa de componente.
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": 0,
                    "parameters": [{"type": "text", "text": button_url_param}],
                }
            )
```

- [ ] **Step 3: Adicionar método `list_message_templates` à classe `CloudAdapter`** (ex: logo antes de `aclose`):

```python
    async def list_message_templates(self, waba_id: str) -> dict[str, Any]:
        """Lista os message templates de um WABA (Graph API).

        Retorna o JSON cru da Graph API: ``{"data": [ {name, status, language,
        category, components}, ... ]}``.
        """
        path = (
            f"/{waba_id}/message_templates"
            "?fields=name,status,language,category,components&limit=200"
        )
        return await self._get_json(path)
```

- [ ] **Step 4: Em `evolution.py`**, atualizar a assinatura de `send_template` para incluir `button_url_param: str | None = None,` (mantendo o corpo que levanta `NotImplementedError`), pra casar com o Protocol. Localizar o `async def send_template(` e acrescentar o parâmetro keyword-only junto dos demais.

- [ ] **Step 5: Verificar lint/type** (CI) nos 3 arquivos.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/whatsapp/base.py apps/api/src/ondeline_api/adapters/whatsapp/cloud.py apps/api/src/ondeline_api/adapters/whatsapp/evolution.py
git commit -m "feat(comunicados-v2): adapter send_template botao dinamico + list_message_templates"
```

---

### Task 6: Serviço de sync de templates (TDD do parser)

**Files:** Create `apps/api/src/ondeline_api/services/whatsapp_templates_sync.py`; Create `apps/api/tests/test_templates_sync.py`

- [ ] **Step 1: Teste do parser (puro) + upsert**

```python
# apps/api/tests/test_templates_sync.py
from __future__ import annotations

import pytest
from sqlalchemy import select

from ondeline_api.db.models.business import BroadcastTemplate
from ondeline_api.services.whatsapp_templates_sync import (
    parse_meta_template,
    upsert_template,
)


def test_parse_body_vars_header_e_botoes() -> None:
    meta = {
        "name": "promo_x",
        "language": "pt_BR",
        "category": "MARKETING",
        "status": "APPROVED",
        "components": [
            {"type": "HEADER", "format": "IMAGE"},
            {"type": "BODY", "text": "Oi {{1}}, veja {{2}}"},
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "URL", "text": "Abrir", "url": "https://x.com/{{1}}"},
                    {"type": "QUICK_REPLY", "text": "Parar"},
                ],
            },
        ],
    }
    out = parse_meta_template(meta)
    assert out["name"] == "promo_x"
    assert out["header_tipo"] == "image"
    assert len(out["variaveis"]) == 2
    assert out["variaveis"][0] == {"indice": 1, "label": "Variável 1", "tipo": "texto"}
    assert out["botoes"][0] == {
        "index": 0, "tipo": "url", "texto": "Abrir", "url_dinamica": True,
    }
    assert out["botoes"][1]["tipo"] == "quick_reply"
    assert out["botoes"][1]["url_dinamica"] is False


def test_parse_sem_componentes() -> None:
    out = parse_meta_template({"name": "x", "language": "pt_BR", "components": []})
    assert out["variaveis"] == []
    assert out["header_tipo"] == "none"
    assert out["botoes"] == []


@pytest.mark.asyncio
async def test_upsert_idempotente(db_session) -> None:
    nome = "tpl_" + __import__("uuid").uuid4().hex[:8]
    spec = {"name": nome, "language": "pt_BR", "category": "MARKETING",
            "variaveis": [], "header_tipo": "none", "botoes": []}
    await upsert_template(db_session, spec)
    await upsert_template(db_session, {**spec, "header_tipo": "image"})
    await db_session.flush()
    rows = list((await db_session.execute(
        select(BroadcastTemplate).where(BroadcastTemplate.name == nome)
    )).scalars().all())
    assert len(rows) == 1
    assert rows[0].header_tipo == "image"
```

- [ ] **Step 2: Rodar (CI) — FAIL**.

- [ ] **Step 3: Implementar o serviço**

```python
# apps/api/src/ondeline_api/services/whatsapp_templates_sync.py
"""Sincronização de templates do WhatsApp Cloud (Graph API) → broadcast_templates.

Puxa os templates APPROVED dos canais Cloud ATIVOS e faz upsert por nome.
"""
from __future__ import annotations

import re
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.whatsapp.cloud import CloudAdapter
from ondeline_api.config import Settings
from ondeline_api.db.models.business import BroadcastTemplate, Canal

log = structlog.get_logger(__name__)

_VAR_RE = re.compile(r"{{(\d+)}}")
_BTN_TIPO = {"url": "url", "quick_reply": "quick_reply", "phone_number": "phone"}


def parse_meta_template(meta: dict[str, Any]) -> dict[str, Any]:
    """Converte um template da Graph API na estrutura do broadcast_templates."""
    variaveis: list[dict[str, Any]] = []
    header_tipo = "none"
    botoes: list[dict[str, Any]] = []
    for comp in meta.get("components") or []:
        ctype = (comp.get("type") or "").upper()
        if ctype == "BODY":
            n = len({int(m) for m in _VAR_RE.findall(comp.get("text") or "")})
            variaveis = [
                {"indice": i, "label": f"Variável {i}", "tipo": "texto"}
                for i in range(1, n + 1)
            ]
        elif ctype == "HEADER":
            header_tipo = "image" if (comp.get("format") or "").upper() == "IMAGE" else "none"
        elif ctype == "BUTTONS":
            for idx, b in enumerate(comp.get("buttons") or []):
                url = b.get("url") or ""
                botoes.append(
                    {
                        "index": idx,
                        "tipo": _BTN_TIPO.get((b.get("type") or "").lower(), (b.get("type") or "").lower()),
                        "texto": b.get("text") or "",
                        "url_dinamica": "{{" in url,
                    }
                )
    return {
        "name": meta["name"],
        "language": meta.get("language") or "pt_BR",
        "category": meta.get("category") or "MARKETING",
        "variaveis": variaveis,
        "header_tipo": header_tipo,
        "botoes": botoes,
    }


async def upsert_template(session: AsyncSession, spec: dict[str, Any]) -> None:
    """Insere ou atualiza um broadcast_template por nome."""
    existing = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == spec["name"])
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            BroadcastTemplate(
                name=spec["name"],
                language=spec["language"],
                category=spec["category"],
                variaveis=spec["variaveis"],
                header_tipo=spec["header_tipo"],
                botoes=spec["botoes"],
                ativo=True,
            )
        )
    else:
        existing.language = spec["language"]
        existing.category = spec["category"]
        existing.variaveis = spec["variaveis"]
        existing.header_tipo = spec["header_tipo"]
        existing.botoes = spec["botoes"]
        existing.ativo = True


async def sincronizar_templates(session: AsyncSession, settings: Settings) -> dict[str, int]:
    """Sincroniza templates APPROVED dos canais Cloud ativos."""
    canais = list(
        (
            await session.execute(
                select(Canal).where(Canal.provider == "cloud", Canal.ativo.is_(True))
            )
        )
        .scalars()
        .all()
    )
    sincronizados = 0
    for canal in canais:
        if not canal.cloud_waba_id:
            continue
        adapter = CloudAdapter(
            access_token=settings.whatsapp_cloud_access_token,
            phone_number_id=canal.cloud_phone_id or "",
            graph_version=settings.whatsapp_cloud_graph_version,
        )
        try:
            data = await adapter.list_message_templates(canal.cloud_waba_id)
        finally:
            await adapter.aclose()
        for meta in data.get("data") or []:
            if (meta.get("status") or "").upper() != "APPROVED":
                continue
            await upsert_template(session, parse_meta_template(meta))
            sincronizados += 1
    await session.commit()
    return {"sincronizados": sincronizados, "canais": len(canais)}
```

> **Nota:** `parse_meta_template` e `upsert_template` são testados diretamente. `sincronizar_templates` é orquestração fina (a chamada HTTP é do adapter, já coberto pelo padrão de retry); não há teste de HTTP aqui.

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/whatsapp_templates_sync.py apps/api/tests/test_templates_sync.py
git commit -m "feat(comunicados-v2): sync de templates da Meta (parse + upsert) + testes"
```

---

### Task 7: broadcast_sender — params por destinatário + botão

**Files:** Modify `apps/api/src/ondeline_api/services/broadcast_sender.py`

- [ ] **Step 1: Adicionar um helper de merge** no topo do módulo (após os imports):

```python
def _merge_params(defaults: list[str] | None, overrides: list[str] | None) -> list[str]:
    """Mescla params por contato com os padrões da campanha.

    Usa o override quando presente e não-vazio; senão o default na mesma posição.
    """
    base = list(defaults or [])
    if not overrides:
        return base
    n = max(len(base), len(overrides))
    out: list[str] = []
    for i in range(n):
        ov = overrides[i] if i < len(overrides) else None
        if ov is not None and ov != "":
            out.append(ov)
        else:
            out.append(base[i] if i < len(base) else "")
    return out
```

- [ ] **Step 2: Em `enviar_destinatario`**, antes do `try:` que chama `send_template`, computar os params e passar o botão. Substituir a chamada de `send_template` para usar os params mesclados:

```python
    body_params = _merge_params(campanha.body_params, destinatario.body_params)
    button_param = destinatario.button_param or campanha.button_param
    try:
        send_result = await adapter.send_template(
            destinatario.whatsapp,
            name=campanha.template_name,
            language=campanha.template_language,
            body_params=body_params,
            header_media_url=campanha.header_media_url,
            button_url_param=button_param,
        )
```

(O restante da função — tratamento de erro, `record_sent`, set de status — permanece igual.)

- [ ] **Step 3: Verificar lint/type** (CI).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/services/broadcast_sender.py
git commit -m "feat(comunicados-v2): sender usa params por destinatario + botao dinamico"
```

---

### Task 8: Parser de import CSV (TDD)

**Files:** Create `apps/api/src/ondeline_api/services/broadcast_import.py`; Create `apps/api/tests/test_broadcast_import.py`

- [ ] **Step 1: Teste**

```python
# apps/api/tests/test_broadcast_import.py
from __future__ import annotations

from ondeline_api.services.broadcast_import import parse_csv_destinatarios

VARIAVEIS = [
    {"indice": 1, "label": "Nome", "tipo": "texto"},
    {"indice": 2, "label": "Link", "tipo": "url"},
]


def test_virgula_com_colunas_de_variaveis() -> None:
    csv_bytes = b"telefone,nome,link\n(92) 99999-9999,Joao,https://a\n"
    rows, invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert invalidos == []
    assert rows[0]["whatsapp"] == "5592999999999"
    assert rows[0]["body_params"] == ["Joao", "https://a"]


def test_ponto_e_virgula_e_coluna_faltando() -> None:
    csv_bytes = "telefone;nome\n5592888888888;Maria\n".encode()
    rows, invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert rows[0]["whatsapp"] == "5592888888888"
    # link ausente vira None (fallback no envio)
    assert rows[0]["body_params"] == ["Maria", None]


def test_telefone_invalido_vai_pra_invalidos() -> None:
    csv_bytes = b"telefone,nome\n999,Bad\n5592777777777,Ok\n"
    rows, invalidos = parse_csv_destinatarios(csv_bytes, VARIAVEIS)
    assert len(rows) == 1
    assert rows[0]["whatsapp"] == "5592777777777"
    assert len(invalidos) == 1


def test_coluna_botao() -> None:
    csv_bytes = b"telefone,botao\n5592111111111,https://btn\n"
    rows, _ = parse_csv_destinatarios(csv_bytes, [])
    assert rows[0]["button_param"] == "https://btn"
```

- [ ] **Step 2: Rodar (CI) — FAIL**.

- [ ] **Step 3: Implementar**

```python
# apps/api/src/ondeline_api/services/broadcast_import.py
"""Parser de CSV de destinatários de campanha.

Coluna de telefone obrigatória; colunas opcionais por variável (casadas por
label normalizado) e uma coluna 'botao'/'link'/'url' para o botão dinâmico.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from typing import Any

from ondeline_api.services.phone import to_cloud_jid

_PHONE_COLS = {"telefone", "whatsapp", "phone", "celular", "fone"}
_BTN_COLS = {"botao", "link", "url"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
    return s


def _detect_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","


def parse_csv_destinatarios(
    content: bytes, variaveis: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Retorna (rows, invalidos).

    Cada row: {whatsapp, body_params: list[str|None] | None, button_param: str|None}.
    invalidos: linhas (texto) cujo telefone não normalizou.
    """
    text = content.decode("utf-8-sig", errors="replace")
    delim = _detect_delimiter(text.splitlines()[0] if text.splitlines() else "")
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    fieldmap = {_norm(h): h for h in (reader.fieldnames or [])}

    phone_key = next((fieldmap[k] for k in fieldmap if k in _PHONE_COLS), None)
    if phone_key is None and reader.fieldnames:
        phone_key = reader.fieldnames[0]
    btn_key = next((fieldmap[k] for k in fieldmap if k in _BTN_COLS), None)

    # mapeia índice da variável -> coluna real (por label normalizado ou "varN")
    var_keys: dict[int, str] = {}
    for v in variaveis:
        idx = int(v["indice"])
        alvo_label = _norm(str(v.get("label") or ""))
        for nk, real in fieldmap.items():
            if nk == alvo_label or nk == f"var{idx}" or nk == f"variavel{idx}":
                var_keys[idx] = real
                break

    rows: list[dict[str, Any]] = []
    invalidos: list[str] = []
    for raw in reader:
        jid = to_cloud_jid(raw.get(phone_key) if phone_key else None)
        if jid is None:
            invalidos.append(delim.join(str(x) for x in raw.values()))
            continue
        body_params: list[str | None] | None = None
        if variaveis:
            n = max(int(v["indice"]) for v in variaveis)
            body_params = [
                (raw.get(var_keys[i]) or None) if i in var_keys else None
                for i in range(1, n + 1)
            ]
        button_param = (raw.get(btn_key) or None) if btn_key else None
        rows.append(
            {"whatsapp": jid, "body_params": body_params, "button_param": button_param}
        )
    return rows, invalidos
```

- [ ] **Step 4: Rodar (CI) — PASS**.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/broadcast_import.py apps/api/tests/test_broadcast_import.py
git commit -m "feat(comunicados-v2): parser de import CSV de destinatarios + testes"
```

---

## FASE 3 — Schemas + API

### Task 9: Schemas

**Files:** Modify `apps/api/src/ondeline_api/api/schemas/comunicado.py`

- [ ] **Step 1: Adicionar/alterar schemas.** Adicionar `TemplateButton`, incluir `botoes` em `BroadcastTemplateOut`, `origem`/`button_param` em `CampanhaCreate`, e novos schemas:

```python
class TemplateButton(BaseModel):
    index: int
    tipo: str
    texto: str
    url_dinamica: bool
```

Em `BroadcastTemplateOut`, adicionar o campo:

```python
    botoes: list[TemplateButton] = []
```

Em `CampanhaCreate`, adicionar:

```python
    origem: str = "segmento"
    button_param: str | None = None
```

Adicionar no fim do arquivo:

```python
class SegmentoValores(BaseModel):
    cidades: list[str]
    status: list[str]
    planos: list[str]


class TemplateUpsert(BaseModel):
    name: str
    language: str = "pt_BR"
    category: str = "MARKETING"
    variaveis: list[TemplateVar] = []
    botoes: list[TemplateButton] = []
    header_tipo: str = "none"
    ativo: bool = True


class SyncResult(BaseModel):
    sincronizados: int
    canais: int


class ImportResult(BaseModel):
    importados: int
    invalidos: int
    amostra_invalidos: list[str]
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/ondeline_api/api/schemas/comunicado.py
git commit -m "feat(comunicados-v2): schemas (botoes, origem, valores, template upsert, import)"
```

---

### Task 10: Endpoints da API

**Files:** Modify `apps/api/src/ondeline_api/api/v1/comunicados.py`

- [ ] **Step 1: Atualizar imports** no topo. Garantir (somando aos existentes):

```python
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
```

e dos schemas/serviços:

```python
from ondeline_api.api.schemas.comunicado import (
    ImportResult,
    SegmentoValores,
    SyncResult,
    TemplateUpsert,
)
from ondeline_api.services.broadcast_import import parse_csv_destinatarios
from ondeline_api.services.segmento import valores_distintos
from ondeline_api.services.whatsapp_templates_sync import sincronizar_templates
from ondeline_api.db.models.business import CampanhaDestinatario
```

(`BroadcastTemplate`, `Campanha`, `Canal`, `Cliente`, `get_settings`, `select` já importados.)

- [ ] **Step 2: Endpoint de valores** — adicionar (antes de `GET /{campanha_id}` por convenção, junto aos outros GET fixos):

```python
@router.get("/segmento/valores", dependencies=[_admin_dep])
async def segmento_valores(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SegmentoValores:
    vals = await valores_distintos(session)
    return SegmentoValores(
        cidades=vals["cidades"], status=vals["status"], planos=vals["planos"]
    )
```

- [ ] **Step 3: Endpoints de template** (sync + manual). Adicionar:

```python
@router.post("/templates/sincronizar", dependencies=[_admin_dep])
async def sincronizar(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResult:
    res = await sincronizar_templates(session, get_settings())
    return SyncResult(sincronizados=res["sincronizados"], canais=res["canais"])


@router.post("/templates", status_code=201, dependencies=[_admin_dep])
async def criar_template(
    body: TemplateUpsert,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BroadcastTemplateOut:
    existing = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == body.name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="template com esse nome já existe")
    t = BroadcastTemplate(
        name=body.name, language=body.language, category=body.category,
        variaveis=[v.model_dump() for v in body.variaveis],
        botoes=[b.model_dump() for b in body.botoes],
        header_tipo=body.header_tipo, ativo=body.ativo,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return BroadcastTemplateOut.model_validate(t, from_attributes=True)


@router.put("/templates/{template_id}", dependencies=[_admin_dep])
async def editar_template(
    template_id: UUID,
    body: TemplateUpsert,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BroadcastTemplateOut:
    t = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.id == template_id)
        )
    ).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="template não encontrado")
    t.name = body.name
    t.language = body.language
    t.category = body.category
    t.variaveis = [v.model_dump() for v in body.variaveis]
    t.botoes = [b.model_dump() for b in body.botoes]
    t.header_tipo = body.header_tipo
    t.ativo = body.ativo
    await session.commit()
    await session.refresh(t)
    return BroadcastTemplateOut.model_validate(t, from_attributes=True)
```

- [ ] **Step 4: Endpoint de import CSV**. Adicionar:

```python
@router.post("/{campanha_id}/destinatarios/importar", dependencies=[_admin_dep])
async def importar_destinatarios(
    campanha_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> ImportResult:
    repo = CampanhaRepo(session)
    camp = await repo.get_by_id(campanha_id)
    if camp is None:
        raise HTTPException(status_code=404, detail="campanha não encontrada")
    if camp.status not in {"rascunho", "erro"}:
        raise HTTPException(status_code=409, detail=f"campanha já está '{camp.status}'")

    tpl = (
        await session.execute(
            select(BroadcastTemplate).where(BroadcastTemplate.name == camp.template_name)
        )
    ).scalar_one_or_none()
    variaveis = tpl.variaveis if tpl is not None else []

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="arquivo vazio")
    rows, invalidos = parse_csv_destinatarios(content, variaveis)

    for r in rows:
        session.add(
            CampanhaDestinatario(
                campanha_id=camp.id,
                cliente_id=None,
                whatsapp=r["whatsapp"],
                body_params=r["body_params"],
                button_param=r["button_param"],
                status="pendente",
            )
        )
    camp.origem = "importado"
    camp.total_destinatarios = len(rows)
    await session.commit()
    return ImportResult(
        importados=len(rows), invalidos=len(invalidos), amostra_invalidos=invalidos[:10]
    )
```

- [ ] **Step 5: Atualizar `create_campanha`** para gravar `origem` e `button_param`. No corpo onde `camp = Campanha(...)` é montado, acrescentar os kwargs:

```python
        origem=body.origem,
        button_param=body.button_param,
```

- [ ] **Step 6: Verificar lint/type** (CI). Conferir ordem das rotas: as rotas fixas (`/templates...`, `/segmento/valores`, `/export/clientes`) devem ficar **antes** de `GET /{campanha_id}` (mesma regra defensiva do v1). A rota `POST /{campanha_id}/destinatarios/importar` (2+ segmentos) não conflita.

- [ ] **Step 7: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/comunicados.py
git commit -m "feat(comunicados-v2): endpoints valores/sync/templates/import + origem na criacao"
```

---

## FASE 4 — Frontend

### Task 11: Tipos + hooks

**Files:** Modify `apps/dashboard/lib/api/types.ts`, `apps/dashboard/lib/api/queries.ts`

- [ ] **Step 1: Tipos** — em `types.ts`, alterar `BroadcastTemplate` e adicionar tipos:

```typescript
export interface BroadcastTemplateButton {
  index: number
  tipo: string
  texto: string
  url_dinamica: boolean
}
```

Adicionar `botoes` à interface `BroadcastTemplate`:

```typescript
  botoes: BroadcastTemplateButton[]
```

Adicionar `origem`/`button_param` à `CampanhaCreate`:

```typescript
  origem?: string
  button_param?: string | null
```

Adicionar:

```typescript
export interface SegmentoValores {
  cidades: string[]
  status: string[]
  planos: string[]
}
export interface ImportResult {
  importados: number
  invalidos: number
  amostra_invalidos: string[]
}
```

- [ ] **Step 2: Hooks** — em `queries.ts`, adicionar:

```typescript
export function useSegmentoValores() {
  return useQuery<import('./types').SegmentoValores>({
    queryKey: ['comunicados-valores'],
    queryFn: () => apiFetch('/api/v1/admin/comunicados/segmento/valores'),
    staleTime: 300_000,
  })
}

export function useSyncTemplates() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ sincronizados: number; canais: number }>(
        '/api/v1/admin/comunicados/templates/sincronizar',
        { method: 'POST' },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['broadcast-templates'] }),
  })
}

export function useImportDestinatarios(campanhaId: string) {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const base = process.env.NEXT_PUBLIC_API_URL ?? ''
      const res = await fetch(
        `${base}/api/v1/admin/comunicados/${campanhaId}/destinatarios/importar`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
          credentials: 'include',
          body: fd,
        },
      )
      if (!res.ok) throw new Error('Falha ao importar CSV')
      return (await res.json()) as import('./types').ImportResult
    },
  })
}
```

> `getAccessToken` já é importado no topo de `queries.ts`. Não setar `Content-Type` no upload (o browser põe o boundary do multipart).

- [ ] **Step 3: Verificar build/types** (CI).

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/lib/api/queries.ts
git commit -m "feat(comunicados-v2): tipos + hooks (valores, sync, import)"
```

---

### Task 12: Formulário de campanha — selects, origem, CSV, botão

**Files:** Modify `apps/dashboard/components/comunicado-form.tsx`

- [ ] **Step 1: Substituir o conteúdo do componente** pelo abaixo (reescreve o arquivo inteiro mantendo imports existentes + novos):

```tsx
'use client'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Download, Send, Upload } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { getAccessToken } from '@/lib/api/token'
import {
  exportClientesUrl,
  useBroadcastTemplates,
  useCanais,
  useCreateCampanha,
  useImportDestinatarios,
  usePreviewSegmento,
  useSegmentoValores,
  useSendCampanha,
} from '@/lib/api/queries'
import type { SegmentoFiltros } from '@/lib/api/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

export function ComunicadoForm() {
  const router = useRouter()
  const { data: templates } = useBroadcastTemplates()
  const { data: canais } = useCanais()
  const { data: valores } = useSegmentoValores()
  const preview = usePreviewSegmento()
  const createCampanha = useCreateCampanha()
  const sendCampanha = useSendCampanha()

  const cloudCanais = useMemo(
    () => (canais ?? []).filter((c) => c.provider === 'cloud'),
    [canais],
  )

  const [titulo, setTitulo] = useState('')
  const [canalId, setCanalId] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [vars, setVars] = useState<Record<number, string>>({})
  const [botao, setBotao] = useState('')
  const [filtros, setFiltros] = useState<SegmentoFiltros>({})
  const [origem, setOrigem] = useState<'segmento' | 'importado'>('segmento')
  const [csvFile, setCsvFile] = useState<File | null>(null)

  const template = templates?.find((t) => t.name === templateName)
  const botaoDinamico = template?.botoes?.find((b) => b.url_dinamica)

  function runPreview() {
    preview.mutate(filtros)
  }

  async function handleExport(fmt: 'csv' | 'xlsx') {
    const path = exportClientesUrl(filtros, fmt)
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
      credentials: 'include',
    })
    if (!res.ok) {
      toast.error('Falha ao exportar')
      return
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `clientes.${fmt}`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  function buildBodyParams(): string[] {
    return (template?.variaveis ?? [])
      .slice()
      .sort((a, b) => a.indice - b.indice)
      .map((v) => vars[v.indice] ?? '')
  }

  async function handleDisparar() {
    if (!template) return
    try {
      const camp = await createCampanha.mutateAsync({
        titulo,
        canal_id: canalId,
        template_name: templateName,
        body_params: buildBodyParams(),
        segmentacao: origem === 'segmento' ? filtros : {},
        origem,
        button_param: botaoDinamico ? botao || null : null,
      })

      let total = preview.data?.total ?? 0
      if (origem === 'importado') {
        if (!csvFile) {
          toast.error('Selecione um CSV')
          return
        }
        const fd = new FormData()
        fd.append('file', csvFile)
        const res = await fetch(
          `${API_URL}/api/v1/admin/comunicados/${camp.id}/destinatarios/importar`,
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
            credentials: 'include',
            body: fd,
          },
        )
        if (!res.ok) {
          toast.error('Falha ao importar CSV')
          return
        }
        const imp = (await res.json()) as { importados: number; invalidos: number }
        total = imp.importados
        toast.success(`${imp.importados} importados, ${imp.invalidos} inválidos`)
      }

      if (!window.confirm(`Disparar para ${total} contato(s)?`)) return
      await sendCampanha.mutateAsync(camp.id)
      toast.success('Campanha enfileirada')
      router.push(`/comunicados/${camp.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao disparar')
    }
  }

  const podeDisparar = titulo && canalId && templateName

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium">Título</label>
        <Input value={titulo} onChange={(e) => setTitulo(e.target.value)}
               placeholder="Ex: Lançamento do app" />
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Canal (Cloud)</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={canalId} onChange={(e) => setCanalId(e.target.value)}>
          <option value="">Selecione…</option>
          {cloudCanais.map((c) => (
            <option key={c.id} value={c.id}>{c.nome}</option>
          ))}
        </select>
        {cloudCanais.length === 0 && (
          <p className="text-xs text-destructive">
            Nenhum canal Cloud cadastrado. Cadastre um em Canais WhatsApp.
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">Template</label>
        <select className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={templateName}
                onChange={(e) => { setTemplateName(e.target.value); setVars({}) }}>
          <option value="">Selecione…</option>
          {(templates ?? []).map((t) => (
            <option key={t.id} value={t.name}>{t.name}</option>
          ))}
        </select>
      </div>

      {template?.variaveis.map((v) => (
        <div key={v.indice} className="space-y-1.5">
          <label className="text-sm font-medium">{v.label}</label>
          <Input
            value={vars[v.indice] ?? ''}
            onChange={(e) => setVars((s) => ({ ...s, [v.indice]: e.target.value }))}
            placeholder={v.tipo === 'url' ? 'https://…' : ''}
          />
        </div>
      ))}

      {botaoDinamico && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Valor do botão ({botaoDinamico.texto})</label>
          <Input value={botao} onChange={(e) => setBotao(e.target.value)} placeholder="https://…" />
        </div>
      )}

      <div className="rounded-md border p-4 space-y-3">
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'segmento'}
                   onChange={() => setOrigem('segmento')} /> Segmento da base
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={origem === 'importado'}
                   onChange={() => setOrigem('importado')} /> Importar CSV
          </label>
        </div>

        {origem === 'segmento' ? (
          <>
            <div className="grid grid-cols-3 gap-3">
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.cidade ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, cidade: e.target.value || undefined }))}>
                <option value="">Cidade (todas)</option>
                {(valores?.cidades ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.status ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, status: e.target.value || undefined }))}>
                <option value="">Status (todos)</option>
                {(valores?.status ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="rounded-md border bg-background px-3 py-2 text-sm"
                      value={filtros.plano ?? ''}
                      onChange={(e) => setFiltros((f) => ({ ...f, plano: e.target.value || undefined }))}>
                <option value="">Plano (todos)</option>
                {(valores?.planos ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={runPreview} type="button"
                      className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                Calcular alcance
              </button>
              {preview.data && (
                <span className="text-sm font-medium">
                  {preview.data.total} cliente(s) vão receber
                </span>
              )}
              <button type="button" onClick={() => handleExport('csv')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> CSV
              </button>
              <button type="button" onClick={() => handleExport('xlsx')}
                      className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm hover:bg-accent">
                <Download className="h-4 w-4" /> Excel
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-2">
            <input type="file" accept=".csv,text/csv"
                   onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
            <p className="text-xs text-muted-foreground">
              CSV com coluna de telefone + colunas opcionais por variável (ex: nome, link).
              O que faltar usa o valor preenchido acima.
            </p>
          </div>
        )}
      </div>

      <button type="button" onClick={handleDisparar} disabled={!podeDisparar}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
        {origem === 'importado' ? <Upload className="h-4 w-4" /> : <Send className="h-4 w-4" />}
        Disparar
      </button>
    </div>
  )
}
```

> Removido o `useImportDestinatarios` da lista de imports se não usado diretamente (o upload está inline no `handleDisparar`). Se o `ruff`/eslint reclamar de import não usado, **retire `useImportDestinatarios` do import**. (Mantê-lo só se for usado.)

- [ ] **Step 2: Ajuste de import** — como o upload está inline, REMOVER `useImportDestinatarios` da lista de imports do `queries` neste arquivo (deixe o hook existindo em queries.ts para uso futuro). Import final deve conter apenas os hooks usados: `exportClientesUrl, useBroadcastTemplates, useCanais, useCreateCampanha, usePreviewSegmento, useSegmentoValores, useSendCampanha`.

- [ ] **Step 3: Verificar build/lint** (CI).

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/components/comunicado-form.tsx
git commit -m "feat(comunicados-v2): form com selects, origem CSV e campo de botao"
```

---

### Task 13: Tela de Templates (lista + sync + cadastro manual)

**Files:** Create `apps/dashboard/app/(admin)/comunicados/templates/page.tsx`, `apps/dashboard/components/comunicado-templates.tsx`

- [ ] **Step 1: Página**

```tsx
// apps/dashboard/app/(admin)/comunicados/templates/page.tsx
import { ComunicadoTemplates } from '@/components/comunicado-templates'

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sincronize os templates aprovados da Meta ou cadastre manualmente.
        </p>
      </div>
      <ComunicadoTemplates />
    </div>
  )
}
```

- [ ] **Step 2: Componente** (lista + botão sincronizar + form manual de criação)

```tsx
// apps/dashboard/components/comunicado-templates.tsx
'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { RefreshCw, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { apiFetch } from '@/lib/api/client'
import { useBroadcastTemplates, useSyncTemplates } from '@/lib/api/queries'
import { useQueryClient } from '@tanstack/react-query'

export function ComunicadoTemplates() {
  const { data: templates, isLoading } = useBroadcastTemplates()
  const sync = useSyncTemplates()
  const qc = useQueryClient()

  const [novoNome, setNovoNome] = useState('')
  const [salvando, setSalvando] = useState(false)

  async function criarManual() {
    if (!novoNome.trim()) return
    setSalvando(true)
    try {
      await apiFetch('/api/v1/admin/comunicados/templates', {
        method: 'POST',
        body: JSON.stringify({ name: novoNome.trim() }),
      })
      toast.success('Template criado')
      setNovoNome('')
      qc.invalidateQueries({ queryKey: ['broadcast-templates'] })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Erro ao criar')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() =>
            sync.mutate(undefined, {
              onSuccess: (r) => toast.success(`${r.sincronizados} sincronizados (${r.canais} canais)`),
              onError: (e) => toast.error(e instanceof Error ? e.message : 'Erro'),
            })
          }
          disabled={sync.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <RefreshCw className="h-4 w-4" /> Sincronizar com a Meta
        </button>
      </div>

      <div className="flex items-end gap-3">
        <div className="space-y-1.5 flex-1 max-w-xs">
          <label className="text-sm font-medium">Cadastrar manual (nome do template)</label>
          <Input value={novoNome} onChange={(e) => setNovoNome(e.target.value)}
                 placeholder="ex: comunicado_geral" />
        </div>
        <button type="button" onClick={criarManual} disabled={salvando}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50">
          <Plus className="h-4 w-4" /> Adicionar
        </button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {templates && (
        <div className="rounded-md border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Nome</th>
                <th className="px-4 py-2.5 font-semibold">Idioma</th>
                <th className="px-4 py-2.5 font-semibold">Variáveis</th>
                <th className="px-4 py-2.5 font-semibold">Botões</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} className="border-b last:border-b-0">
                  <td className="px-4 py-3 font-mono text-xs">{t.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.language}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.variaveis.length}</td>
                  <td className="px-4 py-3">
                    {(t.botoes ?? []).map((b) => (
                      <Badge key={b.index} variant="outline" className="mr-1">
                        {b.texto}{b.url_dinamica ? ' (dinâmico)' : ''}
                      </Badge>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

> Cadastro manual MVP cria só pelo nome (variáveis/botões vêm vazios e podem ser ajustados via sync ou edição futura). A edição completa (PUT) já existe no backend; a UI de edição detalhada fica para iteração futura se necessário — **anotar como follow-up**, não bloquear.

- [ ] **Step 3: Commit**

```bash
git add "apps/dashboard/app/(admin)/comunicados/templates/page.tsx" apps/dashboard/components/comunicado-templates.tsx
git commit -m "feat(comunicados-v2): tela de templates (sync + cadastro manual)"
```

---

### Task 14: Link para Templates na lista de comunicados

**Files:** Modify `apps/dashboard/components/comunicado-list.tsx`

- [ ] **Step 1: Adicionar um link "Templates"** ao lado do botão "Nova campanha". Localizar o `<div className="flex justify-end">` que contém o link de "Nova campanha" e trocar por:

```tsx
      <div className="flex justify-end gap-3">
        <Link
          href="/comunicados/templates"
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent"
        >
          Templates
        </Link>
        <Link
          href="/comunicados/nova"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> Nova campanha
        </Link>
      </div>
```

- [ ] **Step 2: Verificar build** (CI).

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/components/comunicado-list.tsx
git commit -m "feat(comunicados-v2): link Templates na lista de comunicados"
```

---

## FASE 5 — Ajuste de teste existente

### Task 15: Atualizar test_broadcast_task para params por destinatário

**Files:** Modify `apps/api/tests/test_broadcast_task.py`

- [ ] **Step 1: Adicionar um teste** que cobre o merge de params por destinatário. Acrescentar ao fim do arquivo:

```python
@pytest.mark.asyncio
async def test_destinatario_body_params_override(db_session, monkeypatch):
    canal = Canal(slug=f"c3-{uuid4().hex[:8]}", nome="C3", provider="cloud",
                  cloud_phone_id="1", cloud_waba_id="2")
    db_session.add(canal)
    await db_session.flush()
    camp = Campanha(titulo="t", canal_id=canal.id, template_name="promo",
                    body_params=["DEFAULT", "linkpadrao"], segmentacao={},
                    origem="importado", status="rascunho", total_destinatarios=1)
    db_session.add(camp)
    await db_session.flush()
    # destinatário importado com override parcial (só var 1)
    db_session.add(CampanhaDestinatario(
        campanha_id=camp.id, cliente_id=None, whatsapp="5592000",
        body_params=["Joao", None], status="pendente",
    ))
    await db_session.flush()

    captured = {}

    class _Fake:
        async def send_template(self, jid, *, name, language="pt_BR",
                                body_params=None, header_media_url=None,
                                button_url_param=None, **_):
            captured["body_params"] = body_params
            return {"messages": [{"id": "wamid.x"}]}

        async def aclose(self):
            return None

    monkeypatch.setattr("ondeline_api.workers.broadcast.build_for_canal", lambda c, s: _Fake())
    await _send_campanha(db_session, camp.id)
    # var1 do destinatário, var2 cai no default da campanha
    assert captured["body_params"] == ["Joao", "linkpadrao"]
```

- [ ] **Step 2: Rodar (CI) — PASS** (depende das Tasks 1, 7).

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_broadcast_task.py
git commit -m "test(comunicados-v2): merge de params por destinatario no disparo"
```

---

## Self-review (cobertura do spec)

- ✅ Bloco A (filtros dropdown): Task 4 (valores) + Task 10 (endpoint) + Task 11/12 (selects).
- ✅ Bloco B (templates sync+manual com botões): Task 1/2 (botoes), Task 5 (list_message_templates), Task 6 (sync), Task 9/10 (schemas/endpoints), Task 13 (UI).
- ✅ Bloco C (disparo com botões): Task 5 (adapter), Task 7 (sender), Task 12 (campo botão).
- ✅ Bloco D (import CSV): Task 1/2 (cliente_id nullable, params override), Task 3 (to_cloud_jid), Task 8 (parser), Task 10 (endpoint), Task 12 (UI upload), Task 15 (merge no disparo).
- ✅ Sync só de canais Cloud ativos: Task 6 (`Canal.ativo.is_(True)`).
- ✅ Migration 0050: Task 2.
- ✅ Tasks de teste cobrem: phone, valores, sync parse/upsert, import parser, merge no disparo.

## Follow-ups anotados (fora do MVP)
- UI de edição detalhada de template (variáveis/botões na mão) — backend PUT já existe.
- Multi-WABA simultâneo; submissão de templates novos à Meta via API; agendamento; auto-opt-out.
