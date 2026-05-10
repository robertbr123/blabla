# M4 — SGP + Hermes + Tools: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o "ack + escala humano" do M3 por bot real LLM-driven. Hermes (modelo Hermes-3 via gateway OpenAI-compatible em `http://127.0.0.1:8642/v1`) responde, chamando 6 tools (`buscar_cliente_sgp`, `enviar_boleto`, `abrir_ordem_servico`, `transferir_para_humano`, `consultar_planos`, `consultar_manutencoes`) quando precisa de dados ou ações. Cliente conversa fim-a-fim: identifica-se via CPF, recebe boleto, abre OS, escala humano por decisão do LLM. SGP cacheado em Redis com fallback DB.

**Architecture:** `LLMProvider` (interface) + `HermesProvider` (httpx async, OpenAI tool-calling shape). `SgpProvider` (interface) + `SgpOndelineProvider`/`SgpLinkNetAMProvider` (POST `/api/ura/clientes/`) atrás de um `SgpRouter` (tenta Ondeline 1º, fallback LinkNetAM, igual v1). Cache em Redis com TTL config (write-through, fallback persistente em tabela `sgp_cache` do M2). 6 tools em `tools/<nome>.py`, registradas em `tools/registry.py` que exporta o JSON-schema OpenAI. `services/llm_loop.py` faz loop até `max_iter` tool calls. `services/inbound.py` (do M3) tem o branch "ACK_AND_ESCALATE" trocado por chamada ao `llm_loop.run`. FSM evolui: `INICIO → AGUARDA_OPCAO → CLIENTE_CPF → CLIENTE → AGUARDA_ATENDENTE`. Sequência diária `OS-YYYYMMDD-NNN` via tabela nova `os_sequence` (migration `0002`).

**Tech Stack:** httpx async (já em runtime do M3), redis-py async, tudo OpenAI-compatible (não usamos SDK `openai`, falamos HTTP direto pra controlar timeout/retry/JSON). Sem dependências runtime novas além do que M3 já adicionou.

**Pré-requisitos (do M3):**
- Tag `m3-bot-core` aplicada e CI verde
- POST `/webhook` operacional, Celery worker subindo via `make dev`
- `services/inbound.process_inbound_message` retorna `InboundResult` testado com fakes
- `EvolutionAdapter` enviando texto e mídia
- Models `Cliente`, `Conversa`, `Mensagem`, `OrdemServico`, `Tecnico`, `TecnicoArea`, `Manutencao`, `SgpCache`, `LlmEvalSample`, `Config` existentes (do M2)
- Antes de iniciar: confirmar gateway Hermes-3 ativo em `127.0.0.1:8642` com `curl http://127.0.0.1:8642/v1/models` (resposta deve listar `Hermes-3` ou similar)

---

## File Structure (criados/modificados neste M4)

```
apps/api/
├── pyproject.toml                                # NO-OP — deps do M3 cobrem tudo
├── alembic/versions/
│   └── 0002_os_sequence.py                       # NEW — tabela os_sequence(date PK, n) para OS-YYYYMMDD-NNN
├── src/ondeline_api/
│   ├── config.py                                 # MODIFY — fix hermes_model default + LLM_MAX_ITER + LLM_TIMEOUT + LLM_MAX_TOKENS_PER_CONVERSA_DIA + SGP_CACHE_TTL_CLIENTE/FATURAS/NEGATIVO + LLM_HISTORY_TURNS
│   ├── adapters/
│   │   ├── llm/
│   │   │   ├── __init__.py                       # NEW
│   │   │   ├── base.py                           # NEW — LLMProvider, ChatMessage, ChatRequest, ChatResponse, ToolCall, ToolSpec
│   │   │   ├── hermes.py                         # NEW — HermesProvider impl
│   │   │   └── fakes.py                          # NEW — FakeLLMProvider scriptable para testes
│   │   └── sgp/
│   │       ├── __init__.py                       # NEW
│   │       ├── base.py                           # NEW — SgpProvider, ClienteSgp, Fatura, Contrato, EnderecoSgp dataclasses
│   │       ├── ondeline.py                       # NEW
│   │       ├── linknetam.py                      # NEW
│   │       ├── router.py                         # NEW — try Ondeline -> fallback LinkNetAM
│   │       └── fakes.py                          # NEW — FakeSgpProvider scriptable
│   ├── services/
│   │   ├── sgp_cache.py                          # NEW — Redis primary + DB fallback + write-through + negative cache
│   │   ├── llm_loop.py                           # NEW — tool-calling loop com max_iter, fallback escalation
│   │   ├── inbound.py                            # MODIFY — substituir branch ack-and-escalate por llm_loop.run
│   │   ├── pii_mask.py                           # NEW — mask CPF/telefone/email em strings (logs)
│   │   └── tokens_budget.py                      # NEW — circuito de seguranca tokens/conversa/dia
│   ├── tools/
│   │   ├── __init__.py                           # NEW
│   │   ├── registry.py                           # NEW — @tool decorator + ToolRegistry com to_openai_schema()
│   │   ├── context.py                            # NEW — ToolContext (db_session, conversa, cliente, evolution, sgp_router, sgp_cache)
│   │   ├── transferir_para_humano.py             # NEW
│   │   ├── consultar_planos.py                   # NEW
│   │   ├── consultar_manutencoes.py              # NEW
│   │   ├── buscar_cliente_sgp.py                 # NEW
│   │   ├── enviar_boleto.py                      # NEW
│   │   └── abrir_ordem_servico.py                # NEW
│   ├── repositories/
│   │   ├── cliente.py                            # NEW — get_by_cpf_hash, upsert_from_sgp
│   │   ├── ordem_servico.py                      # NEW — create + next_codigo (usa os_sequence)
│   │   ├── tecnico.py                            # NEW — find_by_area(cidade, rua) -> Tecnico|None
│   │   ├── manutencao.py                         # NEW — list_active_in_cidade
│   │   ├── config.py                             # NEW — get(key) -> jsonb
│   │   └── mensagem.py                           # MODIFY — list_history(conversa_id, limit) p/ contexto LLM
│   ├── domain/
│   │   ├── fsm.py                                # MODIFY — extend transitions: ack-and-escalate vira fluxo M4 com tool intents
│   │   └── os_sequence.py                        # NEW — next_codigo(session, date) com SELECT FOR UPDATE atomico
│   └── workers/
│       ├── inbound.py                            # MODIFY — passar SgpRouter + SgpCache + LLMProvider via factory
│       └── runtime.py                            # MODIFY — provider_factories() retornando os singletons (httpx clients reutilizaveis)
└── tests/
    ├── test_llm_provider_base.py
    ├── test_hermes_provider.py
    ├── test_sgp_ondeline.py
    ├── test_sgp_linknetam.py
    ├── test_sgp_router.py
    ├── test_sgp_cache.py
    ├── test_tools_registry.py
    ├── test_tool_transferir_para_humano.py
    ├── test_tool_consultar_planos.py
    ├── test_tool_consultar_manutencoes.py
    ├── test_tool_buscar_cliente_sgp.py
    ├── test_tool_enviar_boleto.py
    ├── test_tool_abrir_ordem_servico.py
    ├── test_os_sequence.py
    ├── test_pii_mask.py
    ├── test_tokens_budget.py
    ├── test_llm_loop.py
    ├── test_repo_cliente.py
    ├── test_repo_tecnico_area.py
    ├── test_fsm_m4.py                            # extensoes de FSM
    └── test_e2e_llm_flow.py                      # synthetic: oi -> CPF -> tool buscar -> tool enviar_boleto -> bot confirma
.env.example                                      # MODIFY — corrigir HERMES_MODEL default + adicionar LLM_*, SGP_CACHE_TTL_*
```

**Princípio de decomposição:**
- `adapters/llm/` e `adapters/sgp/` ficam cada um em pacote próprio com `base.py` (interface) + `<provider>.py` (impls) + `fakes.py` (test doubles em-código). Trocar provider = trocar wiring, não código.
- `tools/` = uma função por arquivo. Cada tool é minúscula (5-30 linhas + schema). Testes 1:1 com tool. Adicionar uma nova tool é criar 1 arquivo + registrar no `registry.py`.
- `services/sgp_cache.py` é o único lugar que sabe da estratégia "Redis primário, DB fallback". Tools chamam `await sgp_cache.get_cliente(cpf_hash)` e ignoram o backend.
- `services/llm_loop.py` faz uma coisa: o loop de tool-calling. Não conhece SGP, não conhece Evolution — recebe um `ToolRegistry` + `LLMProvider` + `ToolContext`.
- `domain/os_sequence.py` é puro SQL (row lock); separa do `OrdemServico` repo para ficar testável isoladamente.

---

## Task 1: Settings, `.env.example`, migration `os_sequence`

**Files:**
- Modify: `apps/api/src/ondeline_api/config.py`
- Modify: `.env.example`
- Create: `apps/api/alembic/versions/0002_os_sequence.py`

- [ ] **Step 1.1: Atualizar `Settings` com campos M4**

Editar `apps/api/src/ondeline_api/config.py`. Substituir o bloco `# Hermes LLM` por:

```python
    # Hermes LLM
    hermes_url: str = "http://127.0.0.1:8642/v1"
    hermes_api_key: str = ""
    hermes_model: str = "Hermes-3"

    # LLM controls
    llm_max_iter: int = 5
    llm_timeout_seconds: float = 30.0
    llm_max_tokens_per_conversa_dia: int = 50_000
    llm_history_turns: int = 12  # ultimas N mensagens incluidas no prompt

    # SGP cache TTL (segundos)
    sgp_cache_ttl_cliente: int = 3600
    sgp_cache_ttl_faturas: int = 300
    sgp_cache_ttl_negativo: int = 300
```

- [ ] **Step 1.2: Atualizar `.env.example`**

Editar `.env.example`. Substituir o bloco Hermes por:

```bash
# Hermes LLM — preenchido em M4
HERMES_URL=http://127.0.0.1:8642/v1
HERMES_API_KEY=
HERMES_MODEL=Hermes-3

# LLM controls
LLM_MAX_ITER=5
LLM_TIMEOUT_SECONDS=30
LLM_MAX_TOKENS_PER_CONVERSA_DIA=50000
LLM_HISTORY_TURNS=12

# SGP cache TTLs (segundos)
SGP_CACHE_TTL_CLIENTE=3600
SGP_CACHE_TTL_FATURAS=300
SGP_CACHE_TTL_NEGATIVO=300
```

- [ ] **Step 1.3: Criar migration `0002_os_sequence`**

Criar `apps/api/alembic/versions/0002_os_sequence.py`:

```python
"""os_sequence table for OS-YYYYMMDD-NNN daily counter.

Revision ID: 0002_os_sequence
Revises: 0001_initial_schema
Create Date: 2026-05-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_os_sequence"
down_revision: str | None = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "os_sequence",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("n", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("os_sequence")
```

- [ ] **Step 1.4: Aplicar migration**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
alembic upgrade head
```

Expected: `Running upgrade 0001_initial_schema -> 0002_os_sequence`.

- [ ] **Step 1.5: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/config.py .env.example apps/api/alembic/versions/0002_os_sequence.py
git commit -m "feat(m4): add LLM/SGP cache settings and os_sequence migration"
```

---

## Task 2: `LLMProvider` interface + dataclasses

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/llm/__init__.py`
- Create: `apps/api/src/ondeline_api/adapters/llm/base.py`
- Create: `apps/api/src/ondeline_api/adapters/llm/fakes.py`
- Create: `apps/api/tests/test_llm_provider_base.py`

- [ ] **Step 2.1: Testes da interface (compatibility shape)**

Criar `apps/api/tests/test_llm_provider_base.py`:

```python
"""LLMProvider interface — types e FakeLLMProvider scriptable."""
from __future__ import annotations

import pytest

from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Role,
    ToolCall,
    ToolSpec,
)
from ondeline_api.adapters.llm.fakes import FakeLLMProvider


pytestmark = pytest.mark.asyncio


def test_chat_message_roles() -> None:
    m = ChatMessage(role=Role.USER, content="oi")
    assert m.role is Role.USER


def test_tool_spec_to_openai_schema() -> None:
    spec = ToolSpec(
        name="my_tool",
        description="faz coisa",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    )
    s = spec.to_openai_schema()
    assert s == {
        "type": "function",
        "function": {
            "name": "my_tool",
            "description": "faz coisa",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
    }


async def test_fake_provider_returns_scripted_response() -> None:
    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Olá! Pode me passar seu CPF?",
                tool_calls=[],
                tokens_used=42,
                finish_reason="stop",
            )
        ]
    )
    out = await fake.chat(
        ChatRequest(
            model="x",
            messages=[ChatMessage(role=Role.USER, content="oi")],
            tools=[],
        )
    )
    assert out.content == "Olá! Pode me passar seu CPF?"
    assert out.tokens_used == 42


async def test_fake_provider_returns_tool_calls() -> None:
    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(id="c1", name="buscar_cliente_sgp", arguments={"cpf_cnpj": "123"})
                ],
                tokens_used=20,
                finish_reason="tool_calls",
            )
        ]
    )
    out = await fake.chat(
        ChatRequest(model="x", messages=[], tools=[])
    )
    assert out.tool_calls and out.tool_calls[0].name == "buscar_cliente_sgp"


async def test_fake_provider_exhausts() -> None:
    fake = FakeLLMProvider(responses=[])
    with pytest.raises(RuntimeError):
        await fake.chat(ChatRequest(model="x", messages=[], tools=[]))
```

- [ ] **Step 2.2: Implementar interface**

Criar `apps/api/src/ondeline_api/adapters/llm/__init__.py`:

```python
"""LLM adapters (interface + Hermes impl + fakes para testes)."""
```

Criar `apps/api/src/ondeline_api/adapters/llm/base.py`:

```python
"""LLMProvider interface — shape OpenAI-compatible.

Tudo que o sistema sabe sobre LLM passa por aqui. Trocar Hermes por outra
coisa = swap de implementacao, sem tocar tools/services.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str | None
    name: str | None = None  # role=tool: nome da tool que respondeu
    tool_call_id: str | None = None  # role=tool: liga a chamada original
    tool_calls: list[ToolCall] | None = None  # role=assistant: tools chamadas


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True, slots=True)
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    tools: list[ToolSpec] = field(default_factory=list)
    temperature: float = 0.4
    max_tokens: int = 800


@dataclass(frozen=True, slots=True)
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall]
    tokens_used: int
    finish_reason: str  # "stop" | "tool_calls" | "length"


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse: ...

    @abstractmethod
    async def aclose(self) -> None: ...
```

Criar `apps/api/src/ondeline_api/adapters/llm/fakes.py`:

```python
"""Fake LLM scriptable para testes de loop e tools."""
from __future__ import annotations

from collections.abc import Sequence

from ondeline_api.adapters.llm.base import ChatRequest, ChatResponse, LLMProvider


class FakeLLMProvider(LLMProvider):
    """Devolve `responses[i]` no i-esimo `chat()`. Falha se exaurir."""

    def __init__(self, responses: Sequence[ChatResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[ChatRequest] = []

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self.calls.append(req)
        if not self._responses:
            raise RuntimeError("FakeLLMProvider exhausted")
        return self._responses.pop(0)

    async def aclose(self) -> None:
        return None
```

- [ ] **Step 2.3: Rodar — devem passar**

```bash
pytest tests/test_llm_provider_base.py -v
```

Expected: `5 passed`.

- [ ] **Step 2.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/adapters/llm/ apps/api/tests/test_llm_provider_base.py
git commit -m "feat(m4): add LLMProvider interface and FakeLLMProvider"
```

---

## Task 3: `HermesProvider` (httpx async, OpenAI tool-calling)

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/llm/hermes.py`
- Create: `apps/api/tests/test_hermes_provider.py`

- [ ] **Step 3.1: Testes com respx**

Criar `apps/api/tests/test_hermes_provider.py`:

```python
"""HermesProvider — POST /v1/chat/completions OpenAI-compatible."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    Role,
    ToolSpec,
)
from ondeline_api.adapters.llm.hermes import HermesProvider


pytestmark = pytest.mark.asyncio

BASE = "http://hermes.test/v1"


def _ok(content: str | None = "Olá!", tool_calls: list | None = None, finish: str = "stop"):
    msg: dict = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "id": "cmpl-1",
        "model": "Hermes-3",
        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 30, "total_tokens": 40},
    }


async def test_basic_chat() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(200, json=_ok("Bem vindo!"))
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=5)
        out = await p.chat(
            ChatRequest(model="Hermes-3", messages=[ChatMessage(role=Role.USER, content="oi")])
        )
        assert out.content == "Bem vindo!"
        assert out.tokens_used == 40
        assert out.finish_reason == "stop"
        await p.aclose()


async def test_tool_calls_parsed() -> None:
    tc = [
        {
            "id": "call_abc",
            "type": "function",
            "function": {
                "name": "buscar_cliente_sgp",
                "arguments": '{"cpf_cnpj": "11122233344"}',
            },
        }
    ]
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(
            200, json=_ok(content=None, tool_calls=tc, finish="tool_calls")
        )
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=5)
        out = await p.chat(
            ChatRequest(
                model="Hermes-3",
                messages=[ChatMessage(role=Role.USER, content="meu cpf eh 11122233344")],
                tools=[
                    ToolSpec(
                        name="buscar_cliente_sgp",
                        description="x",
                        parameters={"type": "object"},
                    )
                ],
            )
        )
        assert out.content is None
        assert len(out.tool_calls) == 1
        assert out.tool_calls[0].name == "buscar_cliente_sgp"
        assert out.tool_calls[0].arguments == {"cpf_cnpj": "11122233344"}
        await p.aclose()


async def test_5xx_raises() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/chat/completions").respond(503, json={"error": "down"})
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=2, retries=0)
        with pytest.raises(RuntimeError):
            await p.chat(
                ChatRequest(model="Hermes-3", messages=[ChatMessage(role=Role.USER, content="x")])
            )
        await p.aclose()


async def test_messages_serialized_with_tool_calls_and_tool_role() -> None:
    """Mensagens role=assistant com tool_calls e role=tool com tool_call_id devem
    ser enviadas no formato OpenAI."""
    captured: dict = {}

    def _cap(request):
        captured["body"] = request.read()
        return Response(200, json=_ok("ok"))

    async with respx.mock() as router:
        router.post(f"{BASE}/chat/completions").mock(side_effect=_cap)
        p = HermesProvider(base_url=BASE, model="Hermes-3", api_key="k", timeout=2)
        await p.chat(
            ChatRequest(
                model="Hermes-3",
                messages=[
                    ChatMessage(role=Role.SYSTEM, content="sys"),
                    ChatMessage(role=Role.USER, content="oi"),
                    ChatMessage(
                        role=Role.ASSISTANT,
                        content=None,
                        tool_calls=[
                            __import__(
                                "ondeline_api.adapters.llm.base",
                                fromlist=["ToolCall"],
                            ).ToolCall(
                                id="call_1",
                                name="t",
                                arguments={"a": 1},
                            )
                        ],
                    ),
                    ChatMessage(
                        role=Role.TOOL,
                        content='{"ok": true}',
                        tool_call_id="call_1",
                        name="t",
                    ),
                ],
            )
        )
        await p.aclose()
    body = captured["body"].decode()
    assert '"role":"system"' in body or '"role": "system"' in body
    assert '"tool_call_id":"call_1"' in body or '"tool_call_id": "call_1"' in body
```

- [ ] **Step 3.2: Implementar `HermesProvider`**

Criar `apps/api/src/ondeline_api/adapters/llm/hermes.py`:

```python
"""HermesProvider — fala HTTP direto com gateway OpenAI-compatible.

Nao usamos o SDK `openai` para manter controle fino sobre timeout/retry/JSON
parsing. O endpoint esperado e `<base>/chat/completions`, no formato
OpenAI v1 (com `tools`/`tool_calls`).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog

from ondeline_api.adapters.llm.base import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
    Role,
    ToolCall,
)


log = structlog.get_logger(__name__)


class HermesProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float = 30.0,
        retries: int = 1,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, req: ChatRequest) -> ChatResponse:
        body = self._serialize(req)
        url = f"{self._base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.post(url, json=body, headers=headers)
                if 200 <= resp.status_code < 300:
                    return self._parse(resp.json())
                if resp.status_code >= 500 and attempt < self._retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Hermes HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except httpx.HTTPError as e:
                if attempt < self._retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"Hermes network error: {e}") from e
        raise RuntimeError("Hermes: exhausted retries")  # defensivo

    # ── serialization ─────────────────────────────────────────

    def _serialize(self, req: ChatRequest) -> dict[str, Any]:
        msgs: list[dict[str, Any]] = []
        for m in req.messages:
            d: dict[str, Any] = {"role": m.role.value}
            if m.content is not None:
                d["content"] = m.content
            if m.role is Role.TOOL:
                d["tool_call_id"] = m.tool_call_id or ""
                if m.name:
                    d["name"] = m.name
            if m.role is Role.ASSISTANT and m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in m.tool_calls
                ]
            msgs.append(d)

        body: dict[str, Any] = {
            "model": req.model or self._model,
            "messages": msgs,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.tools:
            body["tools"] = [t.to_openai_schema() for t in req.tools]
            body["tool_choice"] = "auto"
        return body

    def _parse(self, payload: dict[str, Any]) -> ChatResponse:
        choice = (payload.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        finish = choice.get("finish_reason") or "stop"
        usage = payload.get("usage") or {}
        tool_calls_raw = msg.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for tc in tool_calls_raw:
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                log.warning("hermes.bad_tool_args", raw=fn.get("arguments"))
                args = {}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args)
            )
        return ChatResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            tokens_used=int(usage.get("total_tokens", 0)),
            finish_reason=str(finish),
        )
```

- [ ] **Step 3.3: Rodar testes**

```bash
pytest tests/test_hermes_provider.py -v
```

Expected: `4 passed`.

- [ ] **Step 3.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/adapters/llm/hermes.py apps/api/tests/test_hermes_provider.py
git commit -m "feat(m4): add HermesProvider (OpenAI-compatible chat completions)"
```

---

## Task 4: `SgpProvider` interface + dataclasses

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/sgp/__init__.py`
- Create: `apps/api/src/ondeline_api/adapters/sgp/base.py`
- Create: `apps/api/src/ondeline_api/adapters/sgp/fakes.py`

- [ ] **Step 4.1: Criar interface**

Criar `apps/api/src/ondeline_api/adapters/sgp/__init__.py`:

```python
"""SGP adapters (interface + Ondeline + LinkNetAM + router + fakes)."""
```

Criar `apps/api/src/ondeline_api/adapters/sgp/base.py`:

```python
"""Interface SGP (Sistema de Gestao de Provedor).

Os dois provedores reais (Ondeline e LinkNetAM) compartilham endpoint
`POST /api/ura/clientes/` com body form `{token, app, cpfcnpj}`. O retorno
e uma lista de clientes; cada cliente tem uma lista de `contratos`. Cada
contrato tem `servicos[0].plano.descricao`, `endereco`, `status`, e o
cliente tem `titulos[]` com faturas (link PDF, codigoPix, valor, vencimento).

Isolamos isso atras de uma interface simples para que tools e cache nao
precisem conhecer o shape cru.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


@dataclass(frozen=True, slots=True)
class EnderecoSgp:
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    cep: str = ""
    complemento: str = ""


@dataclass(frozen=True, slots=True)
class Fatura:
    id: str
    valor: float
    vencimento: str  # YYYY-MM-DD
    status: str  # "aberto" | "pago" | ...
    link_pdf: str | None = None
    codigo_pix: str | None = None
    dias_atraso: int = 0


@dataclass(frozen=True, slots=True)
class Contrato:
    id: str
    plano: str
    status: str
    motivo_status: str = ""
    cidade: str = ""


@dataclass(frozen=True, slots=True)
class ClienteSgp:
    provider: SgpProviderEnum
    sgp_id: str
    nome: str
    cpf_cnpj: str  # apenas digitos
    whatsapp: str = ""
    contratos: list[Contrato] = field(default_factory=list)
    endereco: EnderecoSgp = field(default_factory=EnderecoSgp)
    titulos: list[Fatura] = field(default_factory=list)


class SgpProvider(ABC):
    """Implementacao concreta para Ondeline / LinkNetAM. Apenas leitura."""

    name: SgpProviderEnum

    @abstractmethod
    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None: ...

    @abstractmethod
    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]: ...

    @abstractmethod
    async def aclose(self) -> None: ...
```

Criar `apps/api/src/ondeline_api/adapters/sgp/fakes.py`:

```python
"""Fakes SGP scriptaveis."""
from __future__ import annotations

from ondeline_api.adapters.sgp.base import ClienteSgp, Fatura, SgpProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


class FakeSgpProvider(SgpProvider):
    name = SgpProviderEnum.ONDELINE

    def __init__(
        self,
        *,
        clientes: dict[str, ClienteSgp] | None = None,
        faturas: dict[str, list[Fatura]] | None = None,
        raise_on: set[str] | None = None,
    ) -> None:
        self._clientes = clientes or {}
        self._faturas = faturas or {}
        self._raise_on = raise_on or set()

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        if cpf in self._raise_on:
            raise RuntimeError("SGP forced failure")
        return self._clientes.get(cpf)

    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]:
        fts = self._faturas.get(sgp_id, [])
        if apenas_abertas:
            return [f for f in fts if f.status == "aberto"]
        return list(fts)

    async def aclose(self) -> None:
        return None
```

- [ ] **Step 4.2: Smoke import**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
python -c "from ondeline_api.adapters.sgp.base import ClienteSgp, Fatura; from ondeline_api.adapters.sgp.fakes import FakeSgpProvider; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4.3: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/adapters/sgp/__init__.py apps/api/src/ondeline_api/adapters/sgp/base.py apps/api/src/ondeline_api/adapters/sgp/fakes.py
git commit -m "feat(m4): add SgpProvider interface + dataclasses + fake"
```

---

## Task 5: `SgpOndelineProvider` e `SgpLinkNetAMProvider`

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/sgp/ondeline.py`
- Create: `apps/api/src/ondeline_api/adapters/sgp/linknetam.py`
- Create: `apps/api/tests/test_sgp_ondeline.py`
- Create: `apps/api/tests/test_sgp_linknetam.py`

- [ ] **Step 5.1: Implementar Ondeline (template para os dois)**

Criar `apps/api/src/ondeline_api/adapters/sgp/ondeline.py`:

```python
"""SgpOndelineProvider — POST /api/ura/clientes/ form-encoded."""
from __future__ import annotations

import re

import httpx
import structlog

from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
    SgpProvider,
)
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


log = structlog.get_logger(__name__)

_DIGITS_RE = re.compile(r"\D+")


def _clean_cpf(cpf: str) -> str:
    return _DIGITS_RE.sub("", cpf or "")


def _build_endereco(raw: dict | None) -> EnderecoSgp:
    raw = raw or {}
    return EnderecoSgp(
        logradouro=raw.get("logradouro", "") or "",
        numero=raw.get("numero", "") or "",
        bairro=raw.get("bairro", "") or "",
        cidade=raw.get("cidade", "") or "",
        uf=raw.get("uf", "") or "",
        cep=raw.get("cep", "") or "",
        complemento=raw.get("complemento", "") or "",
    )


def _build_fatura(raw: dict) -> Fatura:
    return Fatura(
        id=str(raw.get("id", "")),
        valor=float(raw.get("valorCorrigido") or raw.get("valor") or 0),
        vencimento=str(raw.get("dataVencimento") or ""),
        status=str(raw.get("status") or ""),
        link_pdf=raw.get("link") or None,
        codigo_pix=raw.get("codigoPix") or None,
        dias_atraso=int(raw.get("diasAtraso") or 0),
    )


class SgpOndelineProvider(SgpProvider):
    name = SgpProviderEnum.ONDELINE

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        app: str = "mikrotik",
        timeout: float = 20.0,
        verify_ssl: bool = True,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._app = app
        self._client = httpx.AsyncClient(timeout=timeout, verify=verify_ssl)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        clean = _clean_cpf(cpf)
        if not clean:
            return None
        try:
            r = await self._client.post(
                f"{self._base}/api/ura/clientes/",
                data={"token": self._token, "app": self._app, "cpfcnpj": clean},
            )
        except httpx.HTTPError as e:
            log.warning("sgp.ondeline.network_error", error=str(e))
            return None
        if r.status_code != 200:
            log.warning("sgp.ondeline.http_error", status=r.status_code)
            return None
        try:
            data = r.json()
        except Exception:
            log.warning("sgp.ondeline.json_decode_error")
            return None
        clientes = data if isinstance(data, list) else (data.get("clientes") or [])
        if not clientes:
            return None
        # match exato por cpf
        c = next(
            (cl for cl in clientes if _clean_cpf(cl.get("cpfcnpj", "")) == clean),
            clientes[0],
        )
        contratos_raw = c.get("contratos") or []
        contratos: list[Contrato] = []
        for ct in contratos_raw:
            sv = (ct.get("servicos") or [{}])[0]
            plano = ((sv.get("plano") or {}).get("descricao", "")) or ""
            cidade = (
                (sv.get("endereco") or {}).get("cidade")
                or (ct.get("endereco") or {}).get("cidade")
                or ""
            )
            contratos.append(
                Contrato(
                    id=str(ct.get("id", "")),
                    plano=plano,
                    status=str(ct.get("status", "")),
                    motivo_status=str(ct.get("motivo_status", "") or ""),
                    cidade=cidade,
                )
            )
        titulos = [_build_fatura(t) for t in (c.get("titulos") or [])]
        return ClienteSgp(
            provider=self.name,
            sgp_id=str(c.get("id", "")),
            nome=str(c.get("nome", "")),
            cpf_cnpj=clean,
            whatsapp=str(c.get("celular") or c.get("telefone") or ""),
            contratos=contratos,
            endereco=_build_endereco(c.get("endereco")),
            titulos=titulos,
        )

    async def listar_faturas(self, sgp_id: str, *, apenas_abertas: bool = True) -> list[Fatura]:
        # SGP nao tem endpoint dedicado pra listar faturas por id de cliente
        # — o /api/ura/clientes/ ja retorna `titulos`. Para `listar_faturas`
        # usamos o cache do cliente. Esta funcao e chamada pela tool
        # enviar_boleto que ja tem o ClienteSgp em maos via cache; nao
        # deveria ser invocada diretamente. Deixamos como no-op explicito
        # para evitar requisicoes extras desnecessarias.
        raise NotImplementedError("use ClienteSgp.titulos via sgp_cache")
```

Criar `apps/api/src/ondeline_api/adapters/sgp/linknetam.py`:

```python
"""SgpLinkNetAMProvider — mesmo shape do Ondeline, base + token diferentes."""
from __future__ import annotations

from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


class SgpLinkNetAMProvider(SgpOndelineProvider):
    name = SgpProviderEnum.LINKNETAM
```

- [ ] **Step 5.2: Testes Ondeline**

Criar `apps/api/tests/test_sgp_ondeline.py`:

```python
"""SgpOndelineProvider — POST + parsing."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider


pytestmark = pytest.mark.asyncio

BASE = "http://sgp.test"


def _resp_cliente() -> dict:
    return {
        "clientes": [
            {
                "id": "42",
                "nome": "Maria Silva",
                "cpfcnpj": "111.222.333-44",
                "celular": "5511999999999",
                "endereco": {
                    "logradouro": "Rua A",
                    "numero": "10",
                    "bairro": "Centro",
                    "cidade": "Sao Paulo",
                    "uf": "SP",
                    "cep": "01000-000",
                },
                "contratos": [
                    {
                        "id": "100",
                        "status": "ativo",
                        "servicos": [
                            {
                                "plano": {"descricao": "Premium 100MB"},
                                "endereco": {"cidade": "Sao Paulo"},
                            }
                        ],
                    }
                ],
                "titulos": [
                    {
                        "id": "T1",
                        "valor": 110.0,
                        "valorCorrigido": 115.0,
                        "dataVencimento": "2026-05-15",
                        "status": "aberto",
                        "link": "https://sgp.test/boletos/T1.pdf",
                        "codigoPix": "PIX_T1",
                        "diasAtraso": 0,
                    }
                ],
            }
        ]
    }


async def test_buscar_por_cpf_ok() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json=_resp_cliente())
        p = SgpOndelineProvider(base_url=BASE, token="t", app="mikrotik", timeout=2)
        cli = await p.buscar_por_cpf("111.222.333-44")
        assert cli is not None
        assert cli.sgp_id == "42"
        assert cli.cpf_cnpj == "11122233344"
        assert cli.contratos[0].plano == "Premium 100MB"
        assert cli.contratos[0].cidade == "Sao Paulo"
        assert cli.titulos[0].link_pdf == "https://sgp.test/boletos/T1.pdf"
        assert cli.titulos[0].valor == 115.0
        await p.aclose()


async def test_buscar_nao_encontrado_retorna_none() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json={"clientes": []})
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("00000000000") is None
        await p.aclose()


async def test_buscar_http_error_retorna_none() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(500, json={"err": "x"})
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("11122233344") is None
        await p.aclose()


async def test_buscar_network_error_retorna_none() -> None:
    import httpx as _httpx

    async with respx.mock() as router:
        router.post(f"{BASE}/api/ura/clientes/").mock(
            side_effect=_httpx.ConnectError("boom")
        )
        p = SgpOndelineProvider(base_url=BASE, token="t")
        assert await p.buscar_por_cpf("11122233344") is None
        await p.aclose()


async def test_cpf_vazio_retorna_none() -> None:
    p = SgpOndelineProvider(base_url=BASE, token="t")
    assert await p.buscar_por_cpf("") is None
    await p.aclose()
```

- [ ] **Step 5.3: Testes LinkNetAM (sanity — herda comportamento)**

Criar `apps/api/tests/test_sgp_linknetam.py`:

```python
"""SgpLinkNetAMProvider herda Ondeline; valida apenas o nome do provider."""
from __future__ import annotations

import pytest
import respx

from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


pytestmark = pytest.mark.asyncio


async def test_provider_name() -> None:
    p = SgpLinkNetAMProvider(base_url="http://x", token="t")
    assert p.name is SgpProviderEnum.LINKNETAM
    await p.aclose()


async def test_busca_funciona_e_marca_provider_certo() -> None:
    BASE = "http://link.test"
    payload = {
        "clientes": [
            {"id": "9", "nome": "X", "cpfcnpj": "11122233344", "contratos": [], "titulos": []}
        ]
    }
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(200, json=payload)
        p = SgpLinkNetAMProvider(base_url=BASE, token="t")
        cli = await p.buscar_por_cpf("11122233344")
        assert cli is not None
        assert cli.provider is SgpProviderEnum.LINKNETAM
        await p.aclose()
```

- [ ] **Step 5.4: Rodar — devem passar**

```bash
pytest tests/test_sgp_ondeline.py tests/test_sgp_linknetam.py -v
```

Expected: `7 passed`.

- [ ] **Step 5.5: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/adapters/sgp/ondeline.py apps/api/src/ondeline_api/adapters/sgp/linknetam.py apps/api/tests/test_sgp_ondeline.py apps/api/tests/test_sgp_linknetam.py
git commit -m "feat(m4): add SGP Ondeline + LinkNetAM HTTP providers"
```

---

## Task 6: `SgpRouter` (try Ondeline -> fallback LinkNetAM)

**Files:**
- Create: `apps/api/src/ondeline_api/adapters/sgp/router.py`
- Create: `apps/api/tests/test_sgp_router.py`

- [ ] **Step 6.1: Testes**

Criar `apps/api/tests/test_sgp_router.py`:

```python
"""SgpRouter — tenta primario, fallback secundario."""
from __future__ import annotations

import pytest

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum


pytestmark = pytest.mark.asyncio


def _cli(provider: SgpProviderEnum, sgp_id: str = "1") -> ClienteSgp:
    return ClienteSgp(provider=provider, sgp_id=sgp_id, nome="X", cpf_cnpj="11122233344")


async def test_primario_encontrado_nao_consulta_secundario() -> None:
    primary = FakeSgpProvider(clientes={"11122233344": _cli(SgpProviderEnum.ONDELINE)})
    secondary = FakeSgpProvider()
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("111.222.333-44")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.ONDELINE


async def test_primario_nao_encontrado_consulta_secundario() -> None:
    primary = FakeSgpProvider(clientes={})
    secondary = FakeSgpProvider(
        clientes={"11122233344": _cli(SgpProviderEnum.LINKNETAM, sgp_id="9")}
    )
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("11122233344")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.LINKNETAM


async def test_primario_levanta_consulta_secundario() -> None:
    primary = FakeSgpProvider(raise_on={"11122233344"})
    secondary = FakeSgpProvider(
        clientes={"11122233344": _cli(SgpProviderEnum.LINKNETAM)}
    )
    router = SgpRouter(primary=primary, secondary=secondary)
    cli = await router.buscar_por_cpf("11122233344")
    assert cli is not None
    assert cli.provider is SgpProviderEnum.LINKNETAM


async def test_ambos_falham_retorna_none() -> None:
    primary = FakeSgpProvider(clientes={})
    secondary = FakeSgpProvider(clientes={})
    router = SgpRouter(primary=primary, secondary=secondary)
    assert await router.buscar_por_cpf("11122233344") is None
```

- [ ] **Step 6.2: Implementar router**

Criar `apps/api/src/ondeline_api/adapters/sgp/router.py`:

```python
"""SgpRouter — fan-out sequencial: tenta primario, fallback secundario.

Erros do primario nao sao fatais; logamos e seguimos. Reordenacao por
configuracao no construtor (e o caller que decide quem e Ondeline e quem e
LinkNetAM).
"""
from __future__ import annotations

import structlog

from ondeline_api.adapters.sgp.base import ClienteSgp, Fatura, SgpProvider


log = structlog.get_logger(__name__)


class SgpRouter:
    def __init__(self, *, primary: SgpProvider, secondary: SgpProvider) -> None:
        self._primary = primary
        self._secondary = secondary

    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        for prov in (self._primary, self._secondary):
            try:
                cli = await prov.buscar_por_cpf(cpf)
            except Exception as e:
                log.warning("sgp.router.provider_error", provider=prov.name.value, error=str(e))
                continue
            if cli is not None:
                return cli
        return None

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._secondary.aclose()
```

- [ ] **Step 6.3: Rodar**

```bash
pytest tests/test_sgp_router.py -v
```

Expected: `4 passed`.

- [ ] **Step 6.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/adapters/sgp/router.py apps/api/tests/test_sgp_router.py
git commit -m "feat(m4): add SgpRouter (primary + fallback)"
```

---

## Task 7: `services/sgp_cache.py` (Redis primario + DB fallback)

**Files:**
- Create: `apps/api/src/ondeline_api/services/sgp_cache.py`
- Create: `apps/api/tests/test_sgp_cache.py`

- [ ] **Step 7.1: Testes (fakeredis + Postgres real)**

Criar `apps/api/tests/test_sgp_cache.py`:

```python
"""SgpCache — Redis primario + DB fallback + write-through + negativo."""
from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato, EnderecoSgp, Fatura
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
from ondeline_api.services.sgp_cache import SgpCacheService


pytestmark = pytest.mark.asyncio


def _cli() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Maria",
        cpf_cnpj="11122233344",
        endereco=EnderecoSgp(cidade="SP"),
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        titulos=[Fatura(id="T1", valor=110, vencimento="2026-05-15", status="aberto")],
    )


async def test_miss_chama_router_e_grava_em_redis(db_session) -> None:
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=router,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cli = await cache.get_cliente("11122233344")
    assert cli is not None
    assert cli.sgp_id == "42"

    # 2a chamada: hit (router so foi chamado uma vez por inspecao indireta — segunda call retorna sem o fake levantar excecao mesmo se vazio)
    router2 = SgpRouter(primary=FakeSgpProvider(clientes={}), secondary=FakeSgpProvider())
    cache2 = SgpCacheService(
        redis=cache._redis,  # mesmo redis
        session=db_session,
        router=router2,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cli2 = await cache2.get_cliente("11122233344")
    assert cli2 is not None and cli2.sgp_id == "42"  # serviu do Redis


async def test_negativo_evita_marteladas(db_session) -> None:
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={}), secondary=FakeSgpProvider(clientes={})
    )
    redis = FakeRedis(decode_responses=False)
    cache = SgpCacheService(
        redis=redis, session=db_session, router=router, ttl_cliente=3600, ttl_negativo=300
    )
    a = await cache.get_cliente("00000000000")
    b = await cache.get_cliente("00000000000")
    assert a is None and b is None
    # negativo gravado
    val = await redis.get("sgp:not_found:00000000000")
    assert val is not None


async def test_db_fallback_quando_redis_morto(db_session, monkeypatch) -> None:
    """Se Redis raise, cai no `sgp_cache` table."""
    from ondeline_api.db.models.business import SgpCache

    # popula a tabela manualmente
    db_session.add(
        SgpCache(
            cpf_hash="11122233344",  # simplificado para teste; producao usa hash_pii
            provider=SgpProviderEnum.ONDELINE,
            payload={
                "provider": "ondeline",
                "sgp_id": "42",
                "nome": "Maria",
                "cpf_cnpj": "11122233344",
                "contratos": [],
                "titulos": [],
                "endereco": {},
                "whatsapp": "",
            },
            ttl=3600,
        )
    )
    await db_session.commit()

    class _DeadRedis:
        async def get(self, k):  # noqa: ARG002
            raise RuntimeError("redis down")

        async def set(self, *a, **kw):  # noqa: ARG002
            raise RuntimeError("redis down")

    cache = SgpCacheService(
        redis=_DeadRedis(),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600,
        ttl_negativo=300,
        cpf_hasher=lambda s: s,  # injetavel para teste
    )
    cli = await cache.get_cliente("11122233344")
    assert cli is not None
    assert cli.nome == "Maria"


async def test_invalidate_remove_redis_e_negativo(db_session) -> None:
    redis = FakeRedis(decode_responses=False)
    router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=redis, session=db_session, router=router, ttl_cliente=3600, ttl_negativo=300
    )
    await cache.get_cliente("11122233344")  # popula
    assert await redis.get("sgp:cliente:11122233344") is not None
    await cache.invalidate("11122233344")
    assert await redis.get("sgp:cliente:11122233344") is None
```

- [ ] **Step 7.2: Implementar cache**

Criar `apps/api/src/ondeline_api/services/sgp_cache.py`:

```python
"""SgpCacheService — Redis primario + DB fallback + write-through + negative.

Chaves Redis:
  sgp:cliente:<cpf_hash>   -> JSON do ClienteSgp
  sgp:not_found:<cpf_hash> -> b"1" (TTL menor, evita marteladas)

DB fallback: tabela `sgp_cache` (PK = cpf_hash + provider). Sobrevive a flush
do Redis. Atualizada no mesmo write-through; lida quando Redis dispara excecao.

Hash do cpf usa o `hash_pii` do projeto (HMAC-SHA256 com pepper) por
consistencia com `clientes.cpf_hash`.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
    SgpProvider as SgpProviderInterface,
)
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import hash_pii
from ondeline_api.db.models.business import SgpCache, SgpProvider as SgpProviderEnum


class _RedisProto(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, ex: int | None = None) -> Any: ...
    async def delete(self, *keys: str) -> int: ...


def _serialize_cliente(c: ClienteSgp) -> dict[str, Any]:
    return {
        "provider": c.provider.value,
        "sgp_id": c.sgp_id,
        "nome": c.nome,
        "cpf_cnpj": c.cpf_cnpj,
        "whatsapp": c.whatsapp,
        "contratos": [asdict(ct) for ct in c.contratos],
        "endereco": asdict(c.endereco),
        "titulos": [asdict(t) for t in c.titulos],
    }


def _deserialize_cliente(d: dict[str, Any]) -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum(d["provider"]),
        sgp_id=d["sgp_id"],
        nome=d["nome"],
        cpf_cnpj=d["cpf_cnpj"],
        whatsapp=d.get("whatsapp", ""),
        contratos=[Contrato(**c) for c in d.get("contratos", [])],
        endereco=EnderecoSgp(**d.get("endereco", {})),
        titulos=[Fatura(**t) for t in d.get("titulos", [])],
    )


class SgpCacheService:
    def __init__(
        self,
        *,
        redis: _RedisProto,
        session: AsyncSession,
        router: SgpRouter,
        ttl_cliente: int,
        ttl_negativo: int,
        cpf_hasher: Callable[[str], str] | None = None,
    ) -> None:
        self._redis = redis
        self._session = session
        self._router = router
        self._ttl = ttl_cliente
        self._ttl_neg = ttl_negativo
        self._hasher = cpf_hasher or hash_pii

    # ── public ────────────────────────────────────────────────

    async def get_cliente(self, cpf: str) -> ClienteSgp | None:
        clean = "".join(ch for ch in (cpf or "") if ch.isdigit())
        if not clean:
            return None
        cpf_hash = self._hasher(clean)

        # 1) Redis hit
        try:
            raw = await self._redis.get(f"sgp:cliente:{cpf_hash}")
            if raw:
                return _deserialize_cliente(json.loads(raw))
            neg = await self._redis.get(f"sgp:not_found:{cpf_hash}")
            if neg:
                return None
        except Exception:
            # Redis dead — fallback no DB
            db = await self._read_db(cpf_hash)
            if db is not None:
                return db

        # 2) Miss → router
        cli = await self._router.buscar_por_cpf(clean)
        await self._write(cpf_hash, cli)
        return cli

    async def invalidate(self, cpf: str) -> None:
        clean = "".join(ch for ch in (cpf or "") if ch.isdigit())
        if not clean:
            return
        cpf_hash = self._hasher(clean)
        try:
            await self._redis.delete(f"sgp:cliente:{cpf_hash}", f"sgp:not_found:{cpf_hash}")
        except Exception:
            pass
        # nao apagamos do DB — o write-through proximo sobrescreve

    # ── internal ──────────────────────────────────────────────

    async def _read_db(self, cpf_hash: str) -> ClienteSgp | None:
        stmt = (
            select(SgpCache)
            .where(SgpCache.cpf_hash == cpf_hash)
            .order_by(SgpCache.fetched_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _deserialize_cliente(row.payload)

    async def _write(self, cpf_hash: str, cli: ClienteSgp | None) -> None:
        if cli is None:
            try:
                await self._redis.set(f"sgp:not_found:{cpf_hash}", b"1", ex=self._ttl_neg)
            except Exception:
                pass
            return
        payload = _serialize_cliente(cli)
        try:
            await self._redis.set(
                f"sgp:cliente:{cpf_hash}",
                json.dumps(payload).encode("utf-8"),
                ex=self._ttl,
            )
        except Exception:
            pass

        # write-through DB
        stmt = pg_insert(SgpCache).values(
            cpf_hash=cpf_hash,
            provider=cli.provider,
            payload=payload,
            ttl=self._ttl,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["cpf_hash", "provider"],
            set_={"payload": payload, "ttl": self._ttl, "fetched_at": __import__("sqlalchemy").func.now()},
        )
        await self._session.execute(stmt)
```

- [ ] **Step 7.3: Rodar**

```bash
pytest tests/test_sgp_cache.py -v
```

Expected: `4 passed`.

- [ ] **Step 7.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/services/sgp_cache.py apps/api/tests/test_sgp_cache.py
git commit -m "feat(m4): add SgpCacheService with Redis + DB fallback"
```

---

## Task 8: PII mask + token budget

**Files:**
- Create: `apps/api/src/ondeline_api/services/pii_mask.py`
- Create: `apps/api/src/ondeline_api/services/tokens_budget.py`
- Create: `apps/api/tests/test_pii_mask.py`
- Create: `apps/api/tests/test_tokens_budget.py`

- [ ] **Step 8.1: PII mask + tests**

Criar `apps/api/src/ondeline_api/services/pii_mask.py`:

```python
"""Mascaramento de PII em strings (logs, prompts).

Reduz CPF/CNPJ, telefone BR e email a placeholders. Aplicado em qualquer
log relacionado a LLM (prompts crus tem CPFs).
"""
from __future__ import annotations

import re


_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_PHONE = re.compile(r"\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b")
_EMAIL = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+")


def mask_pii(text: str) -> str:
    if not text:
        return text
    text = _CNPJ.sub("[CNPJ]", text)
    text = _CPF.sub("[CPF]", text)
    text = _PHONE.sub("[PHONE]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    return text
```

Criar `apps/api/tests/test_pii_mask.py`:

```python
from ondeline_api.services.pii_mask import mask_pii


def test_cpf_masked() -> None:
    assert "[CPF]" in mask_pii("meu cpf eh 111.222.333-44")
    assert "[CPF]" in mask_pii("11122233344")


def test_cnpj_masked() -> None:
    assert "[CNPJ]" in mask_pii("12.345.678/0001-90")


def test_phone_masked() -> None:
    assert "[PHONE]" in mask_pii("liga 11 99999-9999")
    assert "[PHONE]" in mask_pii("+55 11 988887777")


def test_email_masked() -> None:
    assert "[EMAIL]" in mask_pii("manda pra a@b.com")


def test_no_match_passthrough() -> None:
    assert mask_pii("ola mundo") == "ola mundo"


def test_empty() -> None:
    assert mask_pii("") == ""
```

- [ ] **Step 8.2: Token budget + tests**

Criar `apps/api/src/ondeline_api/services/tokens_budget.py`:

```python
"""Circuit breaker simples por tokens/conversa/dia.

Usa Redis com chave `llm_budget:<conversa_id>:<YYYYMMDD>` (counter incremental
com TTL ate fim do dia + 1h). Quando excede o limite, sinaliza ao loop pra
escalar humano em vez de chamar LLM.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class _RedisProto(Protocol):
    async def incrby(self, key: str, amount: int) -> int: ...
    async def expire(self, key: str, seconds: int) -> int: ...
    async def get(self, key: str) -> bytes | None: ...


class TokensBudget:
    def __init__(self, redis: _RedisProto, *, daily_limit: int) -> None:
        self._redis = redis
        self._limit = daily_limit

    def _key(self, conversa_id: str) -> str:
        ymd = datetime.now(tz=UTC).strftime("%Y%m%d")
        return f"llm_budget:{conversa_id}:{ymd}"

    async def add(self, conversa_id: str, tokens: int) -> int:
        key = self._key(conversa_id)
        total = int(await self._redis.incrby(key, max(0, tokens)))
        # TTL ate amanha 00:00 UTC + 1h
        now = datetime.now(tz=UTC)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = max(60, int((tomorrow - now).total_seconds()) + 3600)
        await self._redis.expire(key, ttl)
        return total

    async def is_over(self, conversa_id: str) -> bool:
        raw = await self._redis.get(self._key(conversa_id))
        if not raw:
            return False
        try:
            return int(raw) >= self._limit
        except ValueError:
            return False
```

Criar `apps/api/tests/test_tokens_budget.py`:

```python
from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from ondeline_api.services.tokens_budget import TokensBudget


pytestmark = pytest.mark.asyncio


async def test_add_e_over_threshold() -> None:
    b = TokensBudget(FakeRedis(decode_responses=False), daily_limit=100)
    assert (await b.add("c1", 30)) == 30
    assert (await b.add("c1", 30)) == 60
    assert await b.is_over("c1") is False
    assert (await b.add("c1", 50)) == 110
    assert await b.is_over("c1") is True


async def test_outra_conversa_independente() -> None:
    b = TokensBudget(FakeRedis(decode_responses=False), daily_limit=100)
    await b.add("c1", 110)
    assert await b.is_over("c2") is False
```

- [ ] **Step 8.3: Rodar**

```bash
pytest tests/test_pii_mask.py tests/test_tokens_budget.py -v
```

Expected: `8 passed`.

- [ ] **Step 8.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/services/pii_mask.py apps/api/src/ondeline_api/services/tokens_budget.py apps/api/tests/test_pii_mask.py apps/api/tests/test_tokens_budget.py
git commit -m "feat(m4): add PII mask + per-conversa token budget"
```

---

## Task 9: Tools registry + ToolContext

**Files:**
- Create: `apps/api/src/ondeline_api/tools/__init__.py`
- Create: `apps/api/src/ondeline_api/tools/context.py`
- Create: `apps/api/src/ondeline_api/tools/registry.py`
- Create: `apps/api/tests/test_tools_registry.py`

- [ ] **Step 9.1: Implementar ToolContext + registry**

Criar `apps/api/src/ondeline_api/tools/__init__.py`:

```python
"""LLM tool implementations + registry."""
```

Criar `apps/api/src/ondeline_api/tools/context.py`:

```python
"""ToolContext — bundle de dependencias passado a cada execucao de tool.

Tools sao funcoes puras (`async def(ctx, **args) -> dict`) sem estado proprio;
recebem tudo via `ctx`. Isso facilita teste (passar fakes) e swap de provider.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.services.sgp_cache import SgpCacheService


@dataclass
class ToolContext:
    session: AsyncSession
    conversa: Conversa
    cliente: Cliente | None
    evolution: EvolutionAdapter
    sgp_router: SgpRouter
    sgp_cache: SgpCacheService
```

Criar `apps/api/src/ondeline_api/tools/registry.py`:

```python
"""Tool registry — decorator + lookup + JSON Schema export OpenAI-compatible.

Cada tool se auto-registra ao ser importada. O `llm_loop` inicia importando
o pacote `tools` (que importa cada tool), entao chama `registry.specs()` pra
montar a request ao LLM, e `registry.invoke(name, ctx, args)` quando o LLM
chama tools.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ondeline_api.adapters.llm.base import ToolSpec
from ondeline_api.tools.context import ToolContext


ToolFn = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class _Entry:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: ToolFn

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description, parameters=self.parameters)


_REGISTRY: dict[str, _Entry] = {}


def tool(*, name: str, description: str, parameters: dict[str, Any]) -> Callable[[ToolFn], ToolFn]:
    def deco(fn: ToolFn) -> ToolFn:
        if name in _REGISTRY:
            raise ValueError(f"tool '{name}' already registered")
        _REGISTRY[name] = _Entry(name=name, description=description, parameters=parameters, fn=fn)
        return fn

    return deco


def specs() -> list[ToolSpec]:
    return [e.spec for e in _REGISTRY.values()]


def names() -> list[str]:
    return list(_REGISTRY.keys())


async def invoke(name: str, ctx: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    entry = _REGISTRY.get(name)
    if entry is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return await entry.fn(ctx, **arguments)
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"error": f"tool {name} failed: {type(e).__name__}: {e}"}


def reset_for_tests() -> None:
    _REGISTRY.clear()


def force_register(entry: _Entry) -> None:
    """Test helper: bypassa o decorator (uso em tests/test_tools_registry)."""
    _REGISTRY[entry.name] = entry
```

- [ ] **Step 9.2: Testes do registry**

Criar `apps/api/tests/test_tools_registry.py`:

```python
"""Registry de tools — registro, schema OpenAI, invoke, lookup, dedup."""
from __future__ import annotations

import pytest

from ondeline_api.tools import registry as reg


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clean():
    """Salva e restaura o registry global; evita poluir outros testes
    que dependem das tools reais ja registradas via import."""
    saved = dict(reg._REGISTRY)
    reg.reset_for_tests()
    yield
    reg.reset_for_tests()
    reg._REGISTRY.update(saved)


async def test_register_and_invoke() -> None:
    @reg.tool(name="echo", description="echoes", parameters={"type": "object"})
    async def _echo(ctx, **kw):  # noqa: ARG001
        return {"ok": True, "got": kw}

    out = await reg.invoke("echo", ctx=None, arguments={"x": 1})  # type: ignore[arg-type]
    assert out == {"ok": True, "got": {"x": 1}}


async def test_specs_to_openai_schema_has_function_wrapper() -> None:
    @reg.tool(
        name="t",
        description="d",
        parameters={"type": "object", "properties": {"a": {"type": "string"}}},
    )
    async def _t(ctx, **kw):  # noqa: ARG001
        return {}

    [spec] = reg.specs()
    s = spec.to_openai_schema()
    assert s["type"] == "function"
    assert s["function"]["name"] == "t"


async def test_unknown_tool_returns_error() -> None:
    out = await reg.invoke("nope", ctx=None, arguments={})  # type: ignore[arg-type]
    assert "error" in out


async def test_bad_arguments_returns_error() -> None:
    @reg.tool(name="strict", description="", parameters={"type": "object"})
    async def _strict(ctx, *, must_have: str):  # noqa: ARG001
        return {"ok": must_have}

    out = await reg.invoke("strict", ctx=None, arguments={})  # type: ignore[arg-type]
    assert "error" in out


async def test_double_register_raises() -> None:
    @reg.tool(name="dup", description="", parameters={"type": "object"})
    async def _a(ctx, **kw):  # noqa: ARG001
        return {}

    with pytest.raises(ValueError):

        @reg.tool(name="dup", description="", parameters={"type": "object"})
        async def _b(ctx, **kw):  # noqa: ARG001
            return {}
```

- [ ] **Step 9.3: Rodar**

```bash
pytest tests/test_tools_registry.py -v
```

Expected: `5 passed`.

- [ ] **Step 9.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/tools/__init__.py apps/api/src/ondeline_api/tools/context.py apps/api/src/ondeline_api/tools/registry.py apps/api/tests/test_tools_registry.py
git commit -m "feat(m4): add tools registry + ToolContext"
```

---

## Task 10: Tool `transferir_para_humano` (a mais simples — referência)

**Files:**
- Create: `apps/api/src/ondeline_api/tools/transferir_para_humano.py`
- Create: `apps/api/tests/test_tool_transferir_para_humano.py`

- [ ] **Step 10.1: Testes**

Criar `apps/api/tests/test_tool_transferir_para_humano.py`:

```python
"""Tool transferir_para_humano — atualiza status da conversa."""
from __future__ import annotations

from uuid import uuid4

import pytest

from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.transferir_para_humano import (
    SCHEMA,
    transferir_para_humano,
)


pytestmark = pytest.mark.asyncio


async def test_marca_conversa_aguardando(db_session) -> None:
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await transferir_para_humano(ctx, motivo="quer falar com humano")
    assert out["ok"] is True
    assert out["motivo"] == "quer falar com humano"
    await db_session.flush()
    assert conv.status is ConversaStatus.AGUARDANDO
    assert conv.estado is ConversaEstado.AGUARDA_ATENDENTE


def test_schema_estavel() -> None:
    assert SCHEMA["type"] == "object"
    assert "motivo" in SCHEMA["properties"]
```

- [ ] **Step 10.2: Implementar tool**

Criar `apps/api/src/ondeline_api/tools/transferir_para_humano.py`:

```python
"""Tool: transferir conversa para atendente humano."""
from __future__ import annotations

from typing import Any

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "motivo": {
            "type": "string",
            "description": "Motivo curto (ex: 'cliente pediu cancelamento').",
        }
    },
    "required": ["motivo"],
}


@tool(
    name="transferir_para_humano",
    description=(
        "Marca a conversa como aguardando atendente humano. "
        "Use quando o cliente insistir em humano OU quando voce nao "
        "conseguir resolver."
    ),
    parameters=SCHEMA,
)
async def transferir_para_humano(ctx: ToolContext, *, motivo: str) -> dict[str, Any]:
    ctx.conversa.estado = ConversaEstado.AGUARDA_ATENDENTE
    ctx.conversa.status = ConversaStatus.AGUARDANDO
    await ctx.session.flush()
    return {"ok": True, "motivo": motivo}
```

- [ ] **Step 10.3: Rodar**

```bash
pytest tests/test_tool_transferir_para_humano.py -v
```

Expected: `2 passed`.

- [ ] **Step 10.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/tools/transferir_para_humano.py apps/api/tests/test_tool_transferir_para_humano.py
git commit -m "feat(m4): add tool transferir_para_humano"
```

---

## Task 11: Repository `Config` + tool `consultar_planos`

**Files:**
- Create: `apps/api/src/ondeline_api/repositories/config.py`
- Create: `apps/api/src/ondeline_api/tools/consultar_planos.py`
- Create: `apps/api/tests/test_tool_consultar_planos.py`

- [ ] **Step 11.1: Implementar repo Config**

Criar `apps/api/src/ondeline_api/repositories/config.py`:

```python
"""ConfigRepo — get/set jsonb por chave."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Config


class ConfigRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> Any:
        row = (
            await self._session.execute(select(Config.value).where(Config.key == key))
        ).scalar_one_or_none()
        return row

    async def set(self, key: str, value: Any) -> None:
        stmt = pg_insert(Config).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(index_elements=["key"], set_={"value": value})
        await self._session.execute(stmt)
```

- [ ] **Step 11.2: Tool consultar_planos**

Criar `apps/api/src/ondeline_api/tools/consultar_planos.py`:

```python
"""Tool: consultar planos disponiveis (lidos do Config['planos'])."""
from __future__ import annotations

from typing import Any

from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}

_DEFAULT_PLANOS = [
    {"nome": "Essencial", "preco": 110.0, "velocidade": "35MB"},
    {"nome": "Plus", "preco": 130.0, "velocidade": "55MB", "extras": ["IPTV gratis"]},
    {"nome": "Premium", "preco": 150.0, "velocidade": "55MB", "extras": ["IPTV", "camera comodato"]},
]


@tool(
    name="consultar_planos",
    description="Retorna a lista de planos de internet disponiveis com preco e velocidade.",
    parameters=SCHEMA,
)
async def consultar_planos(ctx: ToolContext) -> dict[str, Any]:
    repo = ConfigRepo(ctx.session)
    raw = await repo.get("planos")
    planos = raw if isinstance(raw, list) else _DEFAULT_PLANOS
    return {"planos": planos, "pagamento": ["PIX", "Boleto"]}
```

- [ ] **Step 11.3: Tests**

Criar `apps/api/tests/test_tool_consultar_planos.py`:

```python
"""Tool consultar_planos — usa Config['planos'] ou default."""
from __future__ import annotations

from uuid import uuid4

import pytest

from ondeline_api.db.models.business import Conversa, ConversaEstado, ConversaStatus
from ondeline_api.repositories.config import ConfigRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.consultar_planos import consultar_planos


pytestmark = pytest.mark.asyncio


def _ctx(db_session):
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def test_default_quando_config_vazio(db_session) -> None:
    out = await consultar_planos(_ctx(db_session))
    assert "planos" in out
    assert any(p["nome"] == "Essencial" for p in out["planos"])


async def test_le_do_config_quando_presente(db_session) -> None:
    await ConfigRepo(db_session).set(
        "planos", [{"nome": "X", "preco": 1.0, "velocidade": "1MB"}]
    )
    await db_session.flush()
    out = await consultar_planos(_ctx(db_session))
    assert out["planos"] == [{"nome": "X", "preco": 1.0, "velocidade": "1MB"}]
```

- [ ] **Step 11.4: Rodar**

```bash
pytest tests/test_tool_consultar_planos.py -v
```

Expected: `2 passed`.

- [ ] **Step 11.5: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/repositories/config.py apps/api/src/ondeline_api/tools/consultar_planos.py apps/api/tests/test_tool_consultar_planos.py
git commit -m "feat(m4): add ConfigRepo + tool consultar_planos"
```

---

## Task 12: Tool `consultar_manutencoes`

**Files:**
- Create: `apps/api/src/ondeline_api/repositories/manutencao.py`
- Create: `apps/api/src/ondeline_api/tools/consultar_manutencoes.py`
- Create: `apps/api/tests/test_tool_consultar_manutencoes.py`

- [ ] **Step 12.1: Repo + tool**

Criar `apps/api/src/ondeline_api/repositories/manutencao.py`:

```python
"""ManutencaoRepo — list_active_in_cidade."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Manutencao


class ManutencaoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_in_cidade(self, cidade: str) -> list[Manutencao]:
        now = datetime.now(tz=UTC)
        stmt = select(Manutencao).where(
            Manutencao.inicio_at <= now,
            Manutencao.fim_at >= now,
        )
        all_active = (await self._session.execute(stmt)).scalars().all()
        cidade_lc = (cidade or "").strip().lower()
        if not cidade_lc:
            return list(all_active)
        return [
            m for m in all_active
            if m.cidades is None
            or any(c.strip().lower() == cidade_lc for c in (m.cidades or []))
        ]
```

Criar `apps/api/src/ondeline_api/tools/consultar_manutencoes.py`:

```python
"""Tool: lista manutencoes planejadas que afetam uma cidade."""
from __future__ import annotations

from typing import Any

from ondeline_api.repositories.manutencao import ManutencaoRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"cidade": {"type": "string"}},
    "required": ["cidade"],
}


@tool(
    name="consultar_manutencoes",
    description="Verifica manutencoes planejadas em andamento que afetam uma cidade.",
    parameters=SCHEMA,
)
async def consultar_manutencoes(ctx: ToolContext, *, cidade: str) -> dict[str, Any]:
    repo = ManutencaoRepo(ctx.session)
    items = await repo.list_active_in_cidade(cidade)
    return {
        "manutencoes": [
            {
                "titulo": m.titulo,
                "descricao": m.descricao,
                "inicio_at": m.inicio_at.isoformat(),
                "fim_at": m.fim_at.isoformat(),
            }
            for m in items
        ]
    }
```

Criar `apps/api/tests/test_tool_consultar_manutencoes.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Manutencao,
)
from ondeline_api.tools.consultar_manutencoes import consultar_manutencoes
from ondeline_api.tools.context import ToolContext


pytestmark = pytest.mark.asyncio


def _ctx(db_session):
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def test_lista_filtra_por_cidade(db_session) -> None:
    now = datetime.now(tz=UTC)
    db_session.add_all(
        [
            Manutencao(
                titulo="SP",
                inicio_at=now - timedelta(hours=1),
                fim_at=now + timedelta(hours=2),
                cidades=["Sao Paulo"],
            ),
            Manutencao(
                titulo="RJ",
                inicio_at=now - timedelta(hours=1),
                fim_at=now + timedelta(hours=2),
                cidades=["Rio de Janeiro"],
            ),
            Manutencao(
                titulo="PASSADA",
                inicio_at=now - timedelta(days=2),
                fim_at=now - timedelta(days=1),
                cidades=["Sao Paulo"],
            ),
        ]
    )
    await db_session.flush()
    out = await consultar_manutencoes(_ctx(db_session), cidade="sao paulo")
    titulos = sorted(m["titulo"] for m in out["manutencoes"])
    assert titulos == ["SP"]
```

- [ ] **Step 12.2: Rodar**

```bash
pytest tests/test_tool_consultar_manutencoes.py -v
```

Expected: `1 passed`.

- [ ] **Step 12.3: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/repositories/manutencao.py apps/api/src/ondeline_api/tools/consultar_manutencoes.py apps/api/tests/test_tool_consultar_manutencoes.py
git commit -m "feat(m4): add ManutencaoRepo + tool consultar_manutencoes"
```

---

## Task 13: Repository `Cliente` + tool `buscar_cliente_sgp`

**Files:**
- Create: `apps/api/src/ondeline_api/repositories/cliente.py`
- Create: `apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py`
- Create: `apps/api/tests/test_repo_cliente.py`
- Create: `apps/api/tests/test_tool_buscar_cliente_sgp.py`

- [ ] **Step 13.1: ClienteRepo**

Criar `apps/api/src/ondeline_api/repositories/cliente.py`:

```python
"""ClienteRepo — get_by_cpf_hash + upsert_from_sgp."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.adapters.sgp.base import ClienteSgp
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, SgpProvider as SgpProviderEnum


def _primary_cidade(c: ClienteSgp) -> str:
    if c.contratos:
        for ct in c.contratos:
            if ct.cidade:
                return ct.cidade
    return c.endereco.cidade or ""


def _format_endereco(c: ClienteSgp) -> str:
    e = c.endereco
    parts = [e.logradouro, e.numero, e.bairro, e.cidade, e.uf, e.cep]
    return ", ".join(p for p in parts if p)


class ClienteRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_cpf_hash(self, cpf_hash: str) -> Cliente | None:
        stmt = (
            select(Cliente)
            .where(Cliente.cpf_hash == cpf_hash, Cliente.deleted_at.is_(None))
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_from_sgp(self, c: ClienteSgp, *, whatsapp: str) -> Cliente:
        cpf_hash = hash_pii(c.cpf_cnpj)
        existing = await self.get_by_cpf_hash(cpf_hash)
        plano = c.contratos[0].plano if c.contratos else None
        status = c.contratos[0].status if c.contratos else None
        cidade = _primary_cidade(c)
        endereco = _format_endereco(c)
        provider = (
            SgpProviderEnum.ONDELINE
            if c.provider is SgpProviderEnum.ONDELINE
            else SgpProviderEnum.LINKNETAM
        )
        if existing is not None:
            existing.nome_encrypted = encrypt_pii(c.nome)
            existing.whatsapp = whatsapp or existing.whatsapp
            existing.plano = plano
            existing.status = status
            existing.endereco_encrypted = encrypt_pii(endereco) if endereco else None
            existing.cidade = cidade
            existing.sgp_provider = provider
            existing.sgp_id = c.sgp_id
            await self._session.flush()
            return existing

        novo = Cliente(
            cpf_cnpj_encrypted=encrypt_pii(c.cpf_cnpj),
            cpf_hash=cpf_hash,
            nome_encrypted=encrypt_pii(c.nome),
            whatsapp=whatsapp,
            plano=plano,
            status=status,
            endereco_encrypted=encrypt_pii(endereco) if endereco else None,
            cidade=cidade,
            sgp_provider=provider,
            sgp_id=c.sgp_id,
        )
        self._session.add(novo)
        await self._session.flush()
        return novo
```

- [ ] **Step 13.2: Testes do ClienteRepo**

Criar `apps/api/tests/test_repo_cliente.py`:

```python
"""ClienteRepo: upsert + get_by_cpf_hash."""
from __future__ import annotations

import pytest

from ondeline_api.adapters.sgp.base import ClienteSgp, Contrato, EnderecoSgp
from ondeline_api.db.crypto import decrypt_pii, hash_pii
from ondeline_api.db.models.business import SgpProvider as SgpProviderEnum
from ondeline_api.repositories.cliente import ClienteRepo


pytestmark = pytest.mark.asyncio


def _cli() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Maria",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium 100MB", status="ativo", cidade="Sao Paulo")],
        endereco=EnderecoSgp(logradouro="Rua A", numero="10", cidade="Sao Paulo", uf="SP"),
    )


async def test_insert_e_get(db_session) -> None:
    repo = ClienteRepo(db_session)
    cli = await repo.upsert_from_sgp(_cli(), whatsapp="5511@s")
    assert cli.id is not None
    fetched = await repo.get_by_cpf_hash(hash_pii("11122233344"))
    assert fetched is not None
    assert decrypt_pii(fetched.nome_encrypted) == "Maria"
    assert fetched.cidade == "Sao Paulo"
    assert fetched.plano == "Premium 100MB"


async def test_upsert_atualiza_existente(db_session) -> None:
    repo = ClienteRepo(db_session)
    a = await repo.upsert_from_sgp(_cli(), whatsapp="5511@s")
    cli2 = _cli()
    cli2 = ClienteSgp(
        provider=cli2.provider,
        sgp_id=cli2.sgp_id,
        nome="Maria S",
        cpf_cnpj=cli2.cpf_cnpj,
        contratos=cli2.contratos,
        endereco=cli2.endereco,
    )
    b = await repo.upsert_from_sgp(cli2, whatsapp="5511@s")
    assert a.id == b.id
    assert decrypt_pii(b.nome_encrypted) == "Maria S"
```

- [ ] **Step 13.3: Tool buscar_cliente_sgp**

Criar `apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py`:

```python
"""Tool: busca cliente nos provedores SGP via cache.

Atualiza o `Cliente` no DB e vincula `Conversa.cliente_id`. Retorna dict
mascarado para o LLM (nao vaza CPF, mantem nome/plano/cidade/status mes).
"""
from __future__ import annotations

from typing import Any

from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool
from ondeline_api.repositories.cliente import ClienteRepo


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cpf_cnpj": {
            "type": "string",
            "description": "CPF ou CNPJ; pontuacao opcional (sera limpa).",
        }
    },
    "required": ["cpf_cnpj"],
}


def _resumo_titulos(titulos: list) -> dict[str, Any]:
    abertos = [t for t in titulos if t.status == "aberto"]
    return {
        "abertos": len(abertos),
        "vencimentos": [t.vencimento for t in abertos[:3]],
    }


@tool(
    name="buscar_cliente_sgp",
    description=(
        "Consulta cliente nos provedores SGP (Ondeline + LinkNetAM, nessa ordem). "
        "Use quando o cliente informar CPF ou CNPJ. Retorna nome, plano, status, "
        "cidade e resumo de faturas em aberto."
    ),
    parameters=SCHEMA,
)
async def buscar_cliente_sgp(ctx: ToolContext, *, cpf_cnpj: str) -> dict[str, Any]:
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_cnpj)
    if cli_sgp is None:
        return {"encontrado": False}

    cliente_db = await ClienteRepo(ctx.session).upsert_from_sgp(
        cli_sgp, whatsapp=ctx.conversa.whatsapp
    )
    ctx.conversa.cliente_id = cliente_db.id
    await ctx.session.flush()

    contrato = cli_sgp.contratos[0] if cli_sgp.contratos else None
    return {
        "encontrado": True,
        "nome": cli_sgp.nome,
        "plano": contrato.plano if contrato else None,
        "status_contrato": contrato.status if contrato else None,
        "motivo_status": contrato.motivo_status if contrato else None,
        "cidade": (contrato.cidade if contrato and contrato.cidade else cli_sgp.endereco.cidade),
        "faturas": _resumo_titulos(cli_sgp.titulos),
    }
```

- [ ] **Step 13.4: Tests do tool**

Criar `apps/api/tests/test_tool_buscar_cliente_sgp.py`:

```python
"""Tool buscar_cliente_sgp — usa SgpCacheService + ClienteRepo + vincula conversa."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.buscar_cliente_sgp import buscar_cliente_sgp
from ondeline_api.tools.context import ToolContext


pytestmark = pytest.mark.asyncio


async def test_encontra_e_vincula_conversa(db_session) -> None:
    cli = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[Fatura(id="T1", valor=110, vencimento="2026-05-15", status="aberto")],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE_CPF,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="111.222.333-44")
    assert out["encontrado"] is True
    assert out["nome"] == "Joao"
    assert out["plano"] == "Premium"
    assert out["faturas"]["abertos"] == 1

    # vinculou cliente_id
    await db_session.flush()
    assert conv.cliente_id is not None


async def test_nao_encontrado(db_session) -> None:
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(primary=FakeSgpProvider(), secondary=FakeSgpProvider()),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE_CPF, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await buscar_cliente_sgp(ctx, cpf_cnpj="00000000000")
    assert out == {"encontrado": False}
```

- [ ] **Step 13.5: Rodar**

```bash
pytest tests/test_repo_cliente.py tests/test_tool_buscar_cliente_sgp.py -v
```

Expected: `4 passed`.

- [ ] **Step 13.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/repositories/cliente.py apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py apps/api/tests/test_repo_cliente.py apps/api/tests/test_tool_buscar_cliente_sgp.py
git commit -m "feat(m4): add ClienteRepo + tool buscar_cliente_sgp"
```

---

## Task 14: Tool `enviar_boleto`

**Files:**
- Create: `apps/api/src/ondeline_api/tools/enviar_boleto.py`
- Create: `apps/api/tests/test_tool_enviar_boleto.py`

- [ ] **Step 14.1: Implementar tool**

Criar `apps/api/src/ondeline_api/tools/enviar_boleto.py`:

```python
"""Tool: envia ate N boletos em aberto via Evolution sendMedia.

Le titulos do cache (ou consulta SGP se cache stale via invalidate). Para
cada titulo: envia PDF (link da SGP) + uma mensagem extra com codigoPix.
Invalida cache de cliente apos envio (proxima consulta busca SGP novamente).
"""
from __future__ import annotations

from typing import Any

from ondeline_api.adapters.sgp.base import Fatura
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_boletos": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 3,
        }
    },
}


def _fmt_data(d: str) -> str:
    if d and "-" in d and len(d) == 10:
        y, m, day = d.split("-")
        return f"{day}/{m}/{y}"
    return d


def _build_caption(idx: int, total: int, t: Fatura) -> str:
    venc = _fmt_data(t.vencimento)
    valor = f"R$ {t.valor:.2f}".replace(".", ",")
    cap = (
        f"Fatura {idx + 1} de {total}\n"
        f"Vencimento: {venc}\n"
        f"Valor: {valor}"
    )
    if t.dias_atraso > 0:
        cap += f"\nAtenção: {t.dias_atraso} dia(s) em atraso"
    return cap


@tool(
    name="enviar_boleto",
    description=(
        "Envia ate `max_boletos` faturas em aberto do cliente vinculado a esta "
        "conversa, via PDF + codigo PIX. Use quando o cliente pedir boleto, "
        "fatura, 2a via ou PIX."
    ),
    parameters=SCHEMA,
)
async def enviar_boleto(ctx: ToolContext, *, max_boletos: int = 3) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado a esta conversa"}

    # Recuperamos o ClienteSgp pelo cache (ja deve estar populado pela tool buscar_cliente_sgp).
    # Como o cache usa cpf_hash como chave, e o cpf cleartext nao esta facilmente disponivel
    # aqui, usamos o sgp_id + provider via re-busca da fatura. Para M4 simples, lemos do cache
    # via Cliente.cpf_hash (ja foi consultado e guardado por buscar_cliente_sgp).

    # Atalho: cache mantém ClienteSgp por cpf_hash. Nao temos o cpf cleartext aqui — para
    # nao re-baixar do SGP, mantemos invariante: enviar_boleto so e chamada apos
    # buscar_cliente_sgp (que populou cache). Buscamos o cliente via sgp_id armazenado.
    # Implementacao M4: re-consultar cache usando o cpf hash inverso nao e possivel —
    # entao invocamos sgp_router direto pelo cpf armazenado em Cliente (que esta encrypted).

    from ondeline_api.db.crypto import decrypt_pii

    cpf_clean = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
    cli_sgp = await ctx.sgp_cache.get_cliente(cpf_clean)
    if cli_sgp is None:
        return {"ok": False, "motivo": "cliente nao localizado no SGP"}

    abertos = [t for t in cli_sgp.titulos if t.status == "aberto"]
    if not abertos:
        return {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}

    enviados = 0
    vencimentos: list[str] = []
    n = min(len(abertos), max(1, min(max_boletos, 5)))

    for i, t in enumerate(abertos[:n]):
        if t.link_pdf:
            await ctx.evolution.send_media(
                ctx.conversa.whatsapp,
                url=t.link_pdf,
                mediatype="document",
                mimetype="application/pdf",
                file_name=f"fatura_{t.vencimento or i + 1}.pdf",
                caption=_build_caption(i, n, t),
            )
            enviados += 1
            vencimentos.append(t.vencimento)
        if t.codigo_pix:
            await ctx.evolution.send_text(ctx.conversa.whatsapp, t.codigo_pix)

    # invalida cache pra proxima consulta refletir status atualizado
    await ctx.sgp_cache.invalidate(cpf_clean)
    return {"ok": True, "enviados": enviados, "vencimentos": vencimentos}
```

- [ ] **Step 14.2: Testes (Evolution mocked)**

Criar `apps/api/tests/test_tool_enviar_boleto.py`:

```python
"""Tool enviar_boleto — envia ate N boletos via Evolution mock."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from fakeredis.aioredis import FakeRedis

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.enviar_boleto import enviar_boleto


pytestmark = pytest.mark.asyncio


def _cli_sgp_com_2_faturas() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="X",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[
            Fatura(
                id="T1", valor=110, vencimento="2026-05-15", status="aberto",
                link_pdf="https://sgp/T1.pdf", codigo_pix="PIXPIX_T1"
            ),
            Fatura(
                id="T2", valor=110, vencimento="2026-06-15", status="aberto",
                link_pdf="https://sgp/T2.pdf", codigo_pix="PIXPIX_T2"
            ),
        ],
    )


async def test_envia_2_boletos(db_session) -> None:
    cli_sgp = _cli_sgp_com_2_faturas()
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"11122233344": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("X"),
        whatsapp="5511@s",
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add_all([cliente, conv])
    await db_session.flush()

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "PIX_OUT"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session,
            conversa=conv,
            cliente=cliente,
            evolution=adapter,
            sgp_router=None,  # type: ignore[arg-type]
            sgp_cache=cache,
        )
        out = await enviar_boleto(ctx, max_boletos=2)
        await adapter.aclose()

    assert out["ok"] is True
    assert out["enviados"] == 2
    assert out["vencimentos"] == ["2026-05-15", "2026-06-15"]


async def test_sem_faturas_retorna_ok_zero(db_session) -> None:
    cli_sgp = ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="9",
        nome="Y",
        cpf_cnpj="22233344455",
        contratos=[Contrato(id="200", plano="P", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[],
    )
    cache = SgpCacheService(
        redis=FakeRedis(decode_responses=False),
        session=db_session,
        router=SgpRouter(
            primary=FakeSgpProvider(clientes={"22233344455": cli_sgp}),
            secondary=FakeSgpProvider(),
        ),
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("22233344455"),
        cpf_hash=hash_pii("22233344455"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5512@s",
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5512@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add_all([cliente, conv])
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=cliente,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=cache,
    )
    out = await enviar_boleto(ctx)
    assert out == {"ok": True, "enviados": 0, "mensagem": "Sem faturas em aberto."}


async def test_sem_cliente_falha_grace(db_session) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await enviar_boleto(ctx)
    assert out["ok"] is False
```

- [ ] **Step 14.3: Rodar**

```bash
pytest tests/test_tool_enviar_boleto.py -v
```

Expected: `3 passed`.

- [ ] **Step 14.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/tools/enviar_boleto.py apps/api/tests/test_tool_enviar_boleto.py
git commit -m "feat(m4): add tool enviar_boleto (PDF + PIX via Evolution)"
```

---

## Task 15: `os_sequence` + `TecnicoRepo` + tool `abrir_ordem_servico`

**Files:**
- Create: `apps/api/src/ondeline_api/domain/os_sequence.py`
- Create: `apps/api/src/ondeline_api/repositories/tecnico.py`
- Create: `apps/api/src/ondeline_api/repositories/ordem_servico.py`
- Create: `apps/api/src/ondeline_api/tools/abrir_ordem_servico.py`
- Create: `apps/api/tests/test_os_sequence.py`
- Create: `apps/api/tests/test_repo_tecnico_area.py`
- Create: `apps/api/tests/test_tool_abrir_ordem_servico.py`

- [ ] **Step 15.1: os_sequence (row-locked daily counter)**

Criar `apps/api/src/ondeline_api/domain/os_sequence.py`:

```python
"""Geracao atomica de codigo OS-YYYYMMDD-NNN.

Estrategia: tabela `os_sequence (date PK, n int)` + UPSERT atomico que
incrementa `n` numa unica round-trip (`INSERT ... ON CONFLICT DO UPDATE
SET n = os_sequence.n + 1 RETURNING n`).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_codigo(session: AsyncSession, *, today: date | None = None) -> str:
    d = today or date.today()
    stmt = text(
        """
        INSERT INTO os_sequence (date, n)
        VALUES (:d, 1)
        ON CONFLICT (date) DO UPDATE SET n = os_sequence.n + 1
        RETURNING n
        """
    )
    result = await session.execute(stmt, {"d": d})
    n = int(result.scalar_one())
    return f"OS-{d.strftime('%Y%m%d')}-{n:03d}"
```

Criar `apps/api/tests/test_os_sequence.py`:

```python
"""os_sequence.next_codigo — atomico, formato fixo, sequencial por dia."""
from __future__ import annotations

from datetime import date

import pytest

from ondeline_api.domain.os_sequence import next_codigo


pytestmark = pytest.mark.asyncio


async def test_codigos_sequenciais_no_mesmo_dia(db_session) -> None:
    d = date(2026, 5, 9)
    a = await next_codigo(db_session, today=d)
    b = await next_codigo(db_session, today=d)
    c = await next_codigo(db_session, today=d)
    assert a == "OS-20260509-001"
    assert b == "OS-20260509-002"
    assert c == "OS-20260509-003"


async def test_dia_diferente_reseta(db_session) -> None:
    a = await next_codigo(db_session, today=date(2026, 5, 9))
    b = await next_codigo(db_session, today=date(2026, 5, 10))
    assert a == "OS-20260509-001"
    assert b == "OS-20260510-001"
```

- [ ] **Step 15.2: TecnicoRepo (find_by_area)**

Criar `apps/api/src/ondeline_api/repositories/tecnico.py`:

```python
"""TecnicoRepo: roteamento por (cidade, rua) com prioridade."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import Tecnico, TecnicoArea


class TecnicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_area(self, *, cidade: str, rua: str) -> Tecnico | None:
        cidade_lc = (cidade or "").strip().lower()
        rua_lc = (rua or "").strip().lower()
        stmt = (
            select(Tecnico, TecnicoArea)
            .join(TecnicoArea, TecnicoArea.tecnico_id == Tecnico.id)
            .where(Tecnico.ativo.is_(True))
            .order_by(TecnicoArea.prioridade.asc())
        )
        rows = (await self._session.execute(stmt)).all()
        # ranking simples: prioridade baixa primeiro; tie-break por match exato cidade+rua > so cidade
        best: Tecnico | None = None
        best_score = -1
        for tec, area in rows:
            score = 0
            if (area.cidade or "").lower() == cidade_lc:
                score += 2
            if (area.rua or "").lower() == rua_lc:
                score += 3
            if score > best_score:
                best = tec
                best_score = score
        return best
```

Criar `apps/api/tests/test_repo_tecnico_area.py`:

```python
"""TecnicoRepo.find_by_area — match exato e fallback."""
from __future__ import annotations

import pytest

from ondeline_api.db.models.business import Tecnico, TecnicoArea
from ondeline_api.repositories.tecnico import TecnicoRepo


pytestmark = pytest.mark.asyncio


async def test_match_exato_cidade_rua(db_session) -> None:
    t1 = Tecnico(nome="Pedro", ativo=True)
    t2 = Tecnico(nome="Joana", ativo=True)
    db_session.add_all([t1, t2])
    await db_session.flush()
    db_session.add_all(
        [
            TecnicoArea(tecnico_id=t1.id, cidade="Sao Paulo", rua="Rua A", prioridade=1),
            TecnicoArea(tecnico_id=t2.id, cidade="Sao Paulo", rua="Rua B", prioridade=1),
        ]
    )
    await db_session.flush()
    repo = TecnicoRepo(db_session)
    chosen = await repo.find_by_area(cidade="Sao Paulo", rua="Rua A")
    assert chosen is not None and chosen.id == t1.id


async def test_fallback_cidade_quando_rua_nao_bate(db_session) -> None:
    t = Tecnico(nome="Solo", ativo=True)
    db_session.add(t)
    await db_session.flush()
    db_session.add(
        TecnicoArea(tecnico_id=t.id, cidade="Campinas", rua="Rua X", prioridade=1)
    )
    await db_session.flush()
    repo = TecnicoRepo(db_session)
    chosen = await repo.find_by_area(cidade="Campinas", rua="Rua nao cadastrada")
    assert chosen is not None and chosen.id == t.id


async def test_sem_match_retorna_none(db_session) -> None:
    repo = TecnicoRepo(db_session)
    assert await repo.find_by_area(cidade="Lugar Algum", rua="Y") is None
```

- [ ] **Step 15.3: OrdemServicoRepo + tool**

Criar `apps/api/src/ondeline_api/repositories/ordem_servico.py`:

```python
"""OrdemServicoRepo — create."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ondeline_api.db.models.business import OrdemServico, OsStatus


class OrdemServicoRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        codigo: str,
        cliente_id: UUID,
        tecnico_id: UUID | None,
        problema: str,
        endereco: str,
    ) -> OrdemServico:
        os_ = OrdemServico(
            codigo=codigo,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            problema=problema,
            endereco=endereco,
            status=OsStatus.PENDENTE,
        )
        self._session.add(os_)
        await self._session.flush()
        return os_
```

Criar `apps/api/src/ondeline_api/tools/abrir_ordem_servico.py`:

```python
"""Tool: abre OS, roteia tecnico, notifica via WhatsApp."""
from __future__ import annotations

from typing import Any

from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problema": {
            "type": "string",
            "description": "Descricao curta do problema reportado",
        },
        "endereco": {
            "type": "string",
            "description": "Endereco completo (rua, numero, bairro, cidade)",
        },
    },
    "required": ["problema", "endereco"],
}


def _split_endereco(endereco: str) -> tuple[str, str]:
    """Tentativa best-effort de extrair (rua, cidade) do texto livre."""
    parts = [p.strip() for p in (endereco or "").split(",") if p.strip()]
    rua = parts[0] if parts else ""
    cidade = parts[-2] if len(parts) >= 2 else (parts[-1] if parts else "")
    return rua, cidade


@tool(
    name="abrir_ordem_servico",
    description=(
        "Cria uma Ordem de Servico (OS) tecnica para o cliente vinculado a esta conversa "
        "e roteia para o tecnico mais adequado por cidade/rua. Use quando o problema "
        "tecnico nao puder ser resolvido por orientacao."
    ),
    parameters=SCHEMA,
)
async def abrir_ordem_servico(
    ctx: ToolContext, *, problema: str, endereco: str
) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado"}

    codigo = await next_codigo(ctx.session)
    rua, cidade = _split_endereco(endereco)
    tecnico = await TecnicoRepo(ctx.session).find_by_area(cidade=cidade, rua=rua)
    os_ = await OrdemServicoRepo(ctx.session).create(
        codigo=codigo,
        cliente_id=ctx.cliente.id,
        tecnico_id=tecnico.id if tecnico else None,
        problema=problema,
        endereco=endereco,
    )

    if tecnico is not None and tecnico.whatsapp:
        nome_cliente = decrypt_pii(ctx.cliente.nome_encrypted) if ctx.cliente.nome_encrypted else "Cliente"
        msg = (
            f"Nova OS {codigo}\n"
            f"Cliente: {nome_cliente}\n"
            f"Endereco: {endereco}\n"
            f"Problema: {problema}"
        )
        await ctx.evolution.send_text(tecnico.whatsapp, msg)

    return {
        "ok": True,
        "codigo": codigo,
        "tecnico_nome": tecnico.nome if tecnico else None,
        "os_id": str(os_.id),
    }
```

- [ ] **Step 15.4: Tests da tool abrir_ordem_servico**

Criar `apps/api/tests/test_tool_abrir_ordem_servico.py`:

```python
"""Tool abrir_ordem_servico — cria OS + notifica tecnico."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import (
    Cliente,
    Conversa,
    ConversaEstado,
    ConversaStatus,
    Tecnico,
    TecnicoArea,
)
from ondeline_api.tools.abrir_ordem_servico import abrir_ordem_servico
from ondeline_api.tools.context import ToolContext


pytestmark = pytest.mark.asyncio


async def test_cria_os_com_codigo_e_notifica_tecnico(db_session) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("11122233344"),
        cpf_hash=hash_pii("11122233344"),
        nome_encrypted=encrypt_pii("Joao"),
        whatsapp="5511@s",
        cidade="Sao Paulo",
    )
    tec = Tecnico(nome="Pedro", ativo=True, whatsapp="5511777@s")
    db_session.add_all([cliente, tec])
    await db_session.flush()
    db_session.add(TecnicoArea(tecnico_id=tec.id, cidade="Sao Paulo", rua="Rua A", prioridade=1))
    conv = Conversa(
        id=uuid4(),
        whatsapp="5511@s",
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    BASE = "http://evo.test"
    INST = "hermes-wa"
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OK"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session,
            conversa=conv,
            cliente=cliente,
            evolution=adapter,
            sgp_router=None,  # type: ignore[arg-type]
            sgp_cache=None,  # type: ignore[arg-type]
        )
        out = await abrir_ordem_servico(
            ctx,
            problema="sem internet desde ontem",
            endereco="Rua A, 100, Centro, Sao Paulo, SP",
        )
        await adapter.aclose()

    assert out["ok"] is True
    assert out["codigo"].startswith("OS-")
    assert out["tecnico_nome"] == "Pedro"


async def test_sem_tecnico_disponivel_cria_os_sem_routing(db_session) -> None:
    cliente = Cliente(
        cpf_cnpj_encrypted=encrypt_pii("99988877766"),
        cpf_hash=hash_pii("99988877766"),
        nome_encrypted=encrypt_pii("Y"),
        whatsapp="5519@s",
    )
    db_session.add(cliente)
    conv = Conversa(
        id=uuid4(), whatsapp="5519@s", estado=ConversaEstado.CLIENTE, status=ConversaStatus.BOT
    )
    db_session.add(conv)
    await db_session.flush()
    ctx = ToolContext(
        session=db_session,
        conversa=conv,
        cliente=cliente,
        evolution=None,  # type: ignore[arg-type]
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )
    out = await abrir_ordem_servico(ctx, problema="x", endereco="Rua Inexistente, Cidade Inexistente")
    assert out["ok"] is True
    assert out["tecnico_nome"] is None
```

- [ ] **Step 15.5: Rodar**

```bash
pytest tests/test_os_sequence.py tests/test_repo_tecnico_area.py tests/test_tool_abrir_ordem_servico.py -v
```

Expected: `7 passed`.

- [ ] **Step 15.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/domain/os_sequence.py apps/api/src/ondeline_api/repositories/tecnico.py apps/api/src/ondeline_api/repositories/ordem_servico.py apps/api/src/ondeline_api/tools/abrir_ordem_servico.py apps/api/tests/test_os_sequence.py apps/api/tests/test_repo_tecnico_area.py apps/api/tests/test_tool_abrir_ordem_servico.py
git commit -m "feat(m4): add os_sequence + Tecnico/OS repos + tool abrir_ordem_servico"
```

---

## Task 16: FSM ampliada + helper history

**Files:**
- Modify: `apps/api/src/ondeline_api/domain/fsm.py`
- Modify: `apps/api/src/ondeline_api/repositories/mensagem.py`
- Create: `apps/api/tests/test_fsm_m4.py`

- [ ] **Step 16.1: Adicionar transicoes M4 e nova action LLM_TURN**

Editar `apps/api/src/ondeline_api/domain/fsm.py`. Adicionar uma nova ActionKind e estender a logica:

Substituir o `class ActionKind` por:

```python
class ActionKind(StrEnum):
    SEND_ACK = "send_ack"
    LLM_TURN = "llm_turn"  # M4: pede ao service que rode 1 turno LLM
```

E substituir o corpo do `Fsm.transition` por:

```python
        if event.kind is EventKind.MSG_FROM_ME:
            raise InvalidTransition(
                "FSM should never receive MSG_FROM_ME — filter before invoking."
            )

        # ja em humano: registrar e aguardar atendente — NAO chama LLM, NAO envia ack
        if estado in (ConversaEstado.HUMANO, ConversaEstado.AGUARDA_ATENDENTE):
            return FsmDecision(
                new_estado=estado,
                new_status=status,
                actions=[],
            )

        # encerrada: reabre + LLM cuida da nova interacao desde o inicio
        if estado is ConversaEstado.ENCERRADA:
            return FsmDecision(
                new_estado=ConversaEstado.AGUARDA_OPCAO,
                new_status=ConversaStatus.BOT,
                actions=[Action(kind=ActionKind.LLM_TURN)],
            )

        # demais (INICIO/AGUARDA_OPCAO/CLIENTE_CPF/CLIENTE/LEAD_*): LLM responde.
        # FSM nao decide o destino exato — o LLM, via tool transferir_para_humano,
        # eventualmente move para AGUARDA_ATENDENTE.
        if estado is ConversaEstado.INICIO:
            new_estado = ConversaEstado.AGUARDA_OPCAO
        else:
            new_estado = estado

        return FsmDecision(
            new_estado=new_estado,
            new_status=ConversaStatus.BOT,
            actions=[Action(kind=ActionKind.LLM_TURN)],
        )
```

(ATENCAO: o teste M3 `test_inicio_recebe_msg_cliente_vai_para_humano_e_envia_ack` agora muda — esse comportamento M3 e substituido. Os testes antigos do FSM precisam ser atualizados; veja Step 16.3.)

- [ ] **Step 16.2: list_history em MensagemRepo**

Editar `apps/api/src/ondeline_api/repositories/mensagem.py`. Adicionar metodo:

```python
    async def list_history(
        self, conversa_id: UUID, *, limit: int = 12
    ) -> list[Mensagem]:
        from sqlalchemy import select

        stmt = (
            select(Mensagem)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(reversed(rows))
```

- [ ] **Step 16.3: Atualizar testes M3 existentes (FSM)**

Editar `apps/api/tests/test_fsm.py`. Os testes M3 `test_inicio_recebe_msg_cliente_vai_para_humano_e_envia_ack` e `test_inicio_recebe_imagem_ack_e_humano` esperavam SEND_ACK + HUMANO; agora esperam LLM_TURN + AGUARDA_OPCAO. Substituir corpo por:

```python
def test_inicio_recebe_msg_cliente_vai_para_aguarda_opcao_com_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Oi"),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert decision.new_status is ConversaStatus.BOT
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)


def test_humano_recebe_msg_cliente_apenas_persiste_sem_responder() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.HUMANO,
        status=ConversaStatus.AGUARDANDO,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="Cade?"),
    )
    assert decision.new_estado is ConversaEstado.HUMANO
    assert decision.new_status is ConversaStatus.AGUARDANDO
    assert decision.actions == []


def test_inicio_recebe_imagem_dispara_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.INICIO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_MEDIA, text=None),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)


def test_encerrada_recebe_msg_reabre_e_dispara_llm_turn() -> None:
    decision = Fsm.transition(
        estado=ConversaEstado.ENCERRADA,
        status=ConversaStatus.ENCERRADA,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi de novo"),
    )
    assert decision.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert decision.new_status is ConversaStatus.BOT
    assert any(a.kind is ActionKind.LLM_TURN for a in decision.actions)
```

Remover `test_action_send_ack_carrega_texto_default` (nao mais aplicavel).

- [ ] **Step 16.4: Tests novos M4**

Criar `apps/api/tests/test_fsm_m4.py`:

```python
"""FSM M4 — transicoes adicionais e LLM_TURN action."""
from __future__ import annotations

from ondeline_api.db.models.business import ConversaEstado, ConversaStatus
from ondeline_api.domain.fsm import (
    ActionKind,
    Event,
    EventKind,
    Fsm,
)


def test_aguarda_opcao_segunda_msg_continua_em_aguarda_opcao() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="quero ser cliente"),
    )
    assert d.new_estado is ConversaEstado.AGUARDA_OPCAO
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)


def test_cliente_estado_continua_chamando_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="quero 2a via"),
    )
    assert d.new_estado is ConversaEstado.CLIENTE
    assert any(a.kind is ActionKind.LLM_TURN for a in d.actions)


def test_aguarda_atendente_nao_chama_llm() -> None:
    d = Fsm.transition(
        estado=ConversaEstado.AGUARDA_ATENDENTE,
        status=ConversaStatus.AGUARDANDO,
        event=Event(kind=EventKind.MSG_CLIENTE_TEXT, text="oi atendente"),
    )
    assert d.actions == []
```

- [ ] **Step 16.5: Rodar**

```bash
pytest tests/test_fsm.py tests/test_fsm_m4.py tests/test_repo_mensagem.py -v
```

Expected: testes do FSM atualizados verdes + 3 novos M4 + repo mensagem ainda verde (nao quebramos).

- [ ] **Step 16.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/domain/fsm.py apps/api/src/ondeline_api/repositories/mensagem.py apps/api/tests/test_fsm.py apps/api/tests/test_fsm_m4.py
git commit -m "feat(m4): extend Fsm with LLM_TURN action; add MensagemRepo.list_history"
```

---

## Task 17: `services/llm_loop.py` — tool-calling loop

**Files:**
- Create: `apps/api/src/ondeline_api/services/llm_loop.py`
- Create: `apps/api/tests/test_llm_loop.py`

- [ ] **Step 17.1: System prompt + loop**

Criar `apps/api/src/ondeline_api/services/llm_loop.py`:

```python
"""Loop de tool-calling do LLM.

Recebe a Conversa + ToolContext + LLMProvider. Monta historico (ultimas N
mensagens) + system prompt + tool specs do registry. Itera ate `max_iter`:
  1) chama LLM
  2) se retornou texto sem tool_calls -> envia via Evolution + persiste +
     contabiliza tokens + termina
  3) se retornou tool_calls -> executa cada tool, anexa resultado como
     role=tool, repete

Em qualquer falha (timeout, excecao do provider, budget excedido) escala
para humano via tool transferir_para_humano sintetica + envia mensagem
educada ao cliente.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import structlog

from ondeline_api.adapters.llm.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMProvider,
    Role,
    ToolCall,
)
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.db.models.business import (
    ConversaEstado,
    ConversaStatus,
    Mensagem,
    MensagemRole,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.pii_mask import mask_pii
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools import registry as tools_registry
from ondeline_api.tools.context import ToolContext


log = structlog.get_logger(__name__)


SYSTEM_PROMPT = (
    "Voce e Ondeline, assistente virtual da Ondeline Telecom (provedor de internet "
    "brasileiro). Atende via WhatsApp de forma simpatica, objetiva e profissional.\n\n"
    "REGRAS ABSOLUTAS:\n"
    "- NUNCA diga que e IA; nunca mencione modelo, gateway ou tecnologia.\n"
    "- Respostas curtas, em portugues brasileiro, com emojis leves.\n"
    "- NAO se reapresente se ja existe historico.\n\n"
    "QUANDO O CLIENTE NAO ESTIVER IDENTIFICADO:\n"
    "- Pergunte o CPF (ou CNPJ) e use a tool buscar_cliente_sgp.\n\n"
    "QUANDO O CLIENTE PEDIR BOLETO/2A VIA/PIX:\n"
    "- Confirme e use a tool enviar_boleto.\n\n"
    "QUANDO O CONTRATO ESTIVER ATIVO E HOUVER PROBLEMA TECNICO:\n"
    "- Tente orientar primeiro (luzes do roteador, reinicio).\n"
    "- Se nao resolver, use a tool abrir_ordem_servico.\n\n"
    "QUANDO PRECISAR ESCALAR (cancelamento, reclamacao formal, negociacao de divida, ou cliente insistir):\n"
    "- Avise o cliente e use a tool transferir_para_humano.\n\n"
    "PLANOS:\n"
    "- Use a tool consultar_planos para responder valores/velocidades.\n\n"
    "MANUTENCOES:\n"
    "- Se o cliente reportar instabilidade, considere consultar_manutencoes(cidade) antes de orientar."
)


@dataclass
class LoopOutcome:
    final_text: str | None
    tokens_used: int
    iterations: int
    tool_calls_made: list[str]
    escalated: bool


def _msg_to_chat(m: Mensagem) -> ChatMessage:
    role = (
        Role.USER if m.role is MensagemRole.CLIENTE
        else Role.ASSISTANT if m.role is MensagemRole.BOT
        else Role.ASSISTANT  # atendente
    )
    content = decrypt_pii(m.content_encrypted) if m.content_encrypted else "[midia]"
    return ChatMessage(role=role, content=content)


async def run_turn(
    *,
    ctx: ToolContext,
    provider: LLMProvider,
    model: str,
    history_turns: int,
    max_iter: int,
    budget: TokensBudget | None,
) -> LoopOutcome:
    """Roda um turno completo do bot. Retorna LoopOutcome."""
    tool_calls_made: list[str] = []

    if budget is not None and await budget.is_over(str(ctx.conversa.id)):
        return await _force_escalate(ctx, motivo="orcamento de tokens diario excedido")

    history = await MensagemRepo(ctx.session).list_history(
        ctx.conversa.id, limit=history_turns
    )
    messages: list[ChatMessage] = [
        ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
        *(_msg_to_chat(m) for m in history),
    ]

    total_tokens = 0
    for it in range(max_iter):
        try:
            resp: ChatResponse = await provider.chat(
                ChatRequest(
                    model=model,
                    messages=messages,
                    tools=tools_registry.specs(),
                )
            )
        except Exception as e:
            log.warning("llm_loop.provider_error", error=str(e))
            outcome = await _force_escalate(ctx, motivo="falha tecnica temporaria")
            outcome.iterations = it
            return outcome

        total_tokens += resp.tokens_used

        if not resp.tool_calls:
            text = resp.content or ""
            if text.strip():
                masked_log = mask_pii(text[:100])
                log.info("llm_loop.final", text_preview=masked_log, tokens=total_tokens)
                await ctx.evolution.send_text(ctx.conversa.whatsapp, text)
                await MensagemRepo(ctx.session).insert_bot_reply(
                    conversa_id=ctx.conversa.id, text=text
                )
                if budget is not None:
                    await budget.add(str(ctx.conversa.id), total_tokens)
                return LoopOutcome(
                    final_text=text,
                    tokens_used=total_tokens,
                    iterations=it + 1,
                    tool_calls_made=tool_calls_made,
                    escalated=False,
                )
            # texto vazio sem tool_calls — anomalia; encerra com escalation
            outcome = await _force_escalate(ctx, motivo="resposta vazia do modelo")
            outcome.iterations = it + 1
            return outcome

        # Tool calls — anexa msg assistant + executa cada tool
        messages.append(
            ChatMessage(
                role=Role.ASSISTANT,
                content=None,
                tool_calls=list(resp.tool_calls),
            )
        )
        for tc in resp.tool_calls:
            tool_calls_made.append(tc.name)
            result = await tools_registry.invoke(tc.name, ctx, tc.arguments)
            messages.append(
                ChatMessage(
                    role=Role.TOOL,
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=tc.id,
                    name=tc.name,
                )
            )
            # Se a tool foi transferir_para_humano, a Conversa ja mudou — nao faz sentido continuar
            if tc.name == "transferir_para_humano":
                if budget is not None:
                    await budget.add(str(ctx.conversa.id), total_tokens)
                return LoopOutcome(
                    final_text=None,
                    tokens_used=total_tokens,
                    iterations=it + 1,
                    tool_calls_made=tool_calls_made,
                    escalated=True,
                )

    # Max iter exhausted — escalar
    outcome = await _force_escalate(ctx, motivo="loop excedeu max_iter")
    outcome.tokens_used = total_tokens
    outcome.iterations = max_iter
    outcome.tool_calls_made = tool_calls_made
    return outcome


async def _force_escalate(ctx: ToolContext, *, motivo: str) -> LoopOutcome:
    fallback = (
        "Tive um probleminha tecnico aqui. 😅 Vou te passar pra um atendente humano "
        "para te ajudar agora."
    )
    try:
        await ctx.evolution.send_text(ctx.conversa.whatsapp, fallback)
        await MensagemRepo(ctx.session).insert_bot_reply(
            conversa_id=ctx.conversa.id, text=fallback
        )
    except Exception:
        pass
    ctx.conversa.estado = ConversaEstado.AGUARDA_ATENDENTE
    ctx.conversa.status = ConversaStatus.AGUARDANDO
    await ctx.session.flush()
    log.warning("llm_loop.force_escalate", motivo=motivo)
    return LoopOutcome(
        final_text=fallback,
        tokens_used=0,
        iterations=0,
        tool_calls_made=["transferir_para_humano"],
        escalated=True,
    )
```

- [ ] **Step 17.2: Tests com FakeLLMProvider e respx para Evolution**

Criar `apps/api/tests/test_llm_loop.py`:

```python
"""Loop tool-calling — happy path, com tool, max_iter, escalate."""
from __future__ import annotations

from uuid import uuid4

import pytest
import respx
from fakeredis.aioredis import FakeRedis

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.base import (
    ChatResponse,
    ToolCall,
)
from ondeline_api.adapters.llm.fakes import FakeLLMProvider
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools import registry as tools_registry
from ondeline_api.tools.context import ToolContext

# importar tools garante registro
import ondeline_api.tools.transferir_para_humano  # noqa: F401
import ondeline_api.tools.consultar_planos  # noqa: F401


pytestmark = pytest.mark.asyncio

BASE = "http://evo.test"
INST = "hermes-wa"


def _build_ctx(db_session, conv, evolution):
    return ToolContext(
        session=db_session,
        conversa=conv,
        cliente=None,
        evolution=evolution,
        sgp_router=None,  # type: ignore[arg-type]
        sgp_cache=None,  # type: ignore[arg-type]
    )


async def _seed_first_user_msg(db_session, conv) -> None:
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id,
        external_id="WAEVT_USER_1",
        text="Oi, quais sao os planos?",
        media_type=None,
        media_url=None,
    )
    await db_session.flush()


async def test_resposta_direta_sem_tool(db_session) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Ola! Posso ajudar?", tool_calls=[], tokens_used=20, finish_reason="stop"
            )
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_1"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.final_text == "Ola! Posso ajudar?"
    assert out.escalated is False
    assert out.iterations == 1


async def test_chamada_tool_consultar_planos_e_resposta(db_session) -> None:
    # Garante registry inicializado
    tools_registry.specs()

    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[ToolCall(id="c1", name="consultar_planos", arguments={})],
                tokens_used=15,
                finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Temos Essencial, Plus e Premium! 🚀",
                tool_calls=[],
                tokens_used=25,
                finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_2"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.escalated is False
    assert out.tool_calls_made == ["consultar_planos"]
    assert "Essencial" in (out.final_text or "")


async def test_transferir_para_humano_escala_imediatamente(db_session) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.CLIENTE,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    fake = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="transferir_para_humano",
                        arguments={"motivo": "cliente pediu"},
                    )
                ],
                tokens_used=10,
                finish_reason="tool_calls",
            )
        ]
    )
    adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
    out = await run_turn(
        ctx=_build_ctx(db_session, conv, adapter),
        provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=None,
    )
    await adapter.aclose()
    assert out.escalated is True
    assert conv.estado is ConversaEstado.AGUARDA_ATENDENTE


async def test_provider_excecao_escala_com_mensagem_educada(db_session) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    class BoomProvider(FakeLLMProvider):
        async def chat(self, req):  # noqa: ARG002
            raise RuntimeError("hermes off")

    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_3"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=BoomProvider(responses=[]), model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert out.escalated is True
    assert conv.status is ConversaStatus.AGUARDANDO


async def test_budget_excedido_escala_sem_chamar_provider(db_session) -> None:
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s", estado=ConversaEstado.AGUARDA_OPCAO,
        status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await _seed_first_user_msg(db_session, conv)

    redis = FakeRedis(decode_responses=False)
    budget = TokensBudget(redis, daily_limit=10)
    await budget.add(str(conv.id), 100)  # ja excedeu

    fake = FakeLLMProvider(responses=[])  # se chamar, exhausta
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_4"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        out = await run_turn(
            ctx=_build_ctx(db_session, conv, adapter),
            provider=fake, model="Hermes-3", history_turns=12, max_iter=5, budget=budget,
        )
        await adapter.aclose()
    assert out.escalated is True
```

- [ ] **Step 17.3: Rodar**

```bash
pytest tests/test_llm_loop.py -v
```

Expected: `5 passed`.

- [ ] **Step 17.4: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/services/llm_loop.py apps/api/tests/test_llm_loop.py
git commit -m "feat(m4): add LLM tool-calling loop with budget + escalation fallback"
```

---

## Task 18: Wire — substituir ack-and-escalate em `services/inbound.py`

**Files:**
- Modify: `apps/api/src/ondeline_api/services/inbound.py`
- Modify: `apps/api/src/ondeline_api/workers/runtime.py`
- Modify: `apps/api/src/ondeline_api/workers/inbound.py`
- Modify: `apps/api/tests/test_inbound_service.py` (atualizar fakes para LLM_TURN)

- [ ] **Step 18.1: Substituir ActionKind.SEND_ACK por LLM_TURN no service**

Editar `apps/api/src/ondeline_api/services/inbound.py`. No bloco de actions, substituir:

```python
    escalated = False
    for action in decision.actions:
        if action.kind is ActionKind.SEND_ACK:
            deps.outbound.enqueue_send_outbound(evt.jid, deps.ack_text, conversa.id)
            escalated = True
```

Por:

```python
    escalated = False
    llm_turn_requested = False
    for action in decision.actions:
        if action.kind is ActionKind.LLM_TURN:
            llm_turn_requested = True
        elif action.kind is ActionKind.SEND_ACK:
            # Backward compat M3 — nao usado em M4 (FSM nao emite mais SEND_ACK)
            deps.outbound.enqueue_send_outbound(evt.jid, deps.ack_text, conversa.id)
            escalated = True

    if llm_turn_requested:
        deps.outbound.enqueue_llm_turn(conversa.id)
```

E adicionar ao Protocol `_OutboundQueueProto`:

```python
    def enqueue_llm_turn(self, conversa_id: UUID) -> None: ...
```

(O FakeOutboundQueue do teste M3 vai precisar de uma stub `enqueue_llm_turn` — Step 18.4.)

- [ ] **Step 18.2: Adicionar task `llm_turn_task` no worker**

Criar nova task em `apps/api/src/ondeline_api/workers/llm_turn.py`:

```python
"""Task Celery: roda 1 turno do LLM para uma Conversa."""
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import select

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.hermes import HermesProvider
from ondeline_api.adapters.sgp.linknetam import SgpLinkNetAMProvider
from ondeline_api.adapters.sgp.ondeline import SgpOndelineProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.config import get_settings
from ondeline_api.db.models.business import Cliente, Conversa
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.services.tokens_budget import TokensBudget
from ondeline_api.tools.context import ToolContext
from ondeline_api.workers.celery_app import celery_app
from ondeline_api.workers.runtime import get_redis, task_session

# Importacoes que registram as 6 tools no registry global
import ondeline_api.tools.transferir_para_humano  # noqa: F401
import ondeline_api.tools.consultar_planos  # noqa: F401
import ondeline_api.tools.consultar_manutencoes  # noqa: F401
import ondeline_api.tools.buscar_cliente_sgp  # noqa: F401
import ondeline_api.tools.enviar_boleto  # noqa: F401
import ondeline_api.tools.abrir_ordem_servico  # noqa: F401


log = structlog.get_logger(__name__)


async def _run(conversa_id: UUID) -> dict[str, str | int]:
    s = get_settings()
    redis = await get_redis()
    evolution = EvolutionAdapter(
        base_url=s.evolution_url, instance=s.evolution_instance, api_key=s.evolution_key
    )
    sgp_primary = SgpOndelineProvider(
        base_url=s.sgp_ondeline_base, token=s.sgp_ondeline_token, app=s.sgp_ondeline_app
    )
    sgp_secondary = SgpLinkNetAMProvider(
        base_url=s.sgp_linknetam_base, token=s.sgp_linknetam_token, app=s.sgp_linknetam_app
    )
    router = SgpRouter(primary=sgp_primary, secondary=sgp_secondary)
    provider = HermesProvider(
        base_url=s.hermes_url,
        model=s.hermes_model,
        api_key=s.hermes_api_key,
        timeout=s.llm_timeout_seconds,
    )
    budget = TokensBudget(redis, daily_limit=s.llm_max_tokens_per_conversa_dia)

    try:
        async with task_session() as session:
            conversa = (
                await session.execute(select(Conversa).where(Conversa.id == conversa_id))
            ).scalar_one()
            cliente = None
            if conversa.cliente_id:
                cliente = (
                    await session.execute(
                        select(Cliente).where(Cliente.id == conversa.cliente_id)
                    )
                ).scalar_one_or_none()
            cache = SgpCacheService(
                redis=redis,
                session=session,
                router=router,
                ttl_cliente=s.sgp_cache_ttl_cliente,
                ttl_negativo=s.sgp_cache_ttl_negativo,
            )
            ctx = ToolContext(
                session=session,
                conversa=conversa,
                cliente=cliente,
                evolution=evolution,
                sgp_router=router,
                sgp_cache=cache,
            )
            outcome = await run_turn(
                ctx=ctx,
                provider=provider,
                model=s.hermes_model,
                history_turns=s.llm_history_turns,
                max_iter=s.llm_max_iter,
                budget=budget,
            )
        log.info(
            "llm_turn.done",
            conversa_id=str(conversa_id),
            tokens=outcome.tokens_used,
            iterations=outcome.iterations,
            tools=outcome.tool_calls_made,
            escalated=outcome.escalated,
        )
        return {
            "conversa_id": str(conversa_id),
            "tokens": outcome.tokens_used,
            "iterations": outcome.iterations,
            "escalated": str(outcome.escalated).lower(),
        }
    finally:
        await provider.aclose()
        await router.aclose()
        await evolution.aclose()


@celery_app.task(
    name="ondeline_api.workers.llm_turn.llm_turn_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def llm_turn_task(self, *, conversa_id: str) -> dict[str, str | int]:
    try:
        return asyncio.run(_run(UUID(conversa_id)))
    except Exception as e:
        raise self.retry(exc=e)
```

E em `workers/celery_app.py`, adicionar `"ondeline_api.workers.llm_turn"` ao `include` e o routing:

```python
        include=[
            "ondeline_api.workers.inbound",
            "ondeline_api.workers.outbound",
            "ondeline_api.workers.llm_turn",
        ],
```

E em `task_routes`:

```python
            "ondeline_api.workers.llm_turn.llm_turn_task": {"queue": "llm"},
```

- [ ] **Step 18.3: Atualizar `runtime.py` com Redis singleton e enqueue LLM turn**

Editar `apps/api/src/ondeline_api/workers/runtime.py`. Adicionar:

```python
import redis.asyncio as aioredis


_redis_singleton: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_singleton
    if _redis_singleton is None:
        from ondeline_api.config import get_settings

        _redis_singleton = aioredis.from_url(get_settings().redis_url, decode_responses=False)
    return _redis_singleton
```

E estender `CeleryOutboundEnqueuer`:

```python
    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        from ondeline_api.workers.llm_turn import llm_turn_task

        llm_turn_task.delay(conversa_id=str(conversa_id))
```

- [ ] **Step 18.4: Atualizar `test_inbound_service.py` com LLM_TURN no fake**

Editar `apps/api/tests/test_inbound_service.py`. Substituir o `FakeOutboundQueue`:

```python
@dataclass
class FakeOutboundQueue:
    sent: list[tuple[str, str, UUID]] = field(default_factory=list)
    llm_turns: list[UUID] = field(default_factory=list)

    def enqueue_send_outbound(self, jid: str, text: str, conversa_id: UUID) -> None:
        self.sent.append((jid, text, conversa_id))

    def enqueue_llm_turn(self, conversa_id: UUID) -> None:
        self.llm_turns.append(conversa_id)
```

E os testes que esperavam `repos.outbound.sent` agora esperam `repos.outbound.llm_turns` (M4 desativou ack direto). Substituir asserts:

- `test_text_msg_inicio_envia_ack_e_marca_humano` → renomear para `test_text_msg_inicio_enfileira_llm_turn`; assert `out.escalated is False` (escalation agora vem do LLM); `len(repos.outbound.llm_turns) == 1`.
- `test_humano_nao_envia_ack_repetido` → 1ª msg dispara `llm_turn`, 2ª (em HUMANO segundo o NOVO FSM permanece em estado anterior; lembre que M4 FSM so retorna [] em HUMANO/AGUARDA_ATENDENTE — entao 2 msg consecutivas em HUMANO não disparam LLM). Asserts: `len(llm_turns) == 1`.

Atualizar com cuidado conforme novo comportamento — o teste de `image` igualmente passa a verificar `llm_turns`.

- [ ] **Step 18.5: Rodar todos os testes regressao**

```bash
pytest tests/test_inbound_service.py tests/test_celery_inbound_task.py -v
```

Expected: verde.

- [ ] **Step 18.6: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/src/ondeline_api/services/inbound.py apps/api/src/ondeline_api/workers/llm_turn.py apps/api/src/ondeline_api/workers/celery_app.py apps/api/src/ondeline_api/workers/runtime.py apps/api/tests/test_inbound_service.py
git commit -m "feat(m4): wire llm_turn_task into inbound flow (replaces ack-and-escalate)"
```

---

## Task 19: E2E sintetico (oi -> CPF -> tool buscar -> tool enviar_boleto)

**Files:**
- Create: `apps/api/tests/test_e2e_llm_flow.py`

- [ ] **Step 19.1: Teste E2E**

Criar `apps/api/tests/test_e2e_llm_flow.py`:

```python
"""E2E sintetico do fluxo LLM:
  cliente: 'Oi'
  bot: 'Pode passar o CPF?'  (FakeLLM resp 1)
  cliente: '11122233344'
  bot: tool buscar_cliente_sgp -> tool resp ok -> bot 'Encontrei!'  (FakeLLM resp 2 + 3)
  cliente: 'manda boleto'
  bot: tool enviar_boleto -> bot 'Enviado!'  (FakeLLM resp 4 + 5)
"""
from __future__ import annotations

from uuid import uuid4
from unittest.mock import patch

import pytest
import respx
from fakeredis.aioredis import FakeRedis

from ondeline_api.adapters.evolution import EvolutionAdapter
from ondeline_api.adapters.llm.base import ChatResponse, ToolCall
from ondeline_api.adapters.llm.fakes import FakeLLMProvider
from ondeline_api.adapters.sgp.base import (
    ClienteSgp,
    Contrato,
    EnderecoSgp,
    Fatura,
)
from ondeline_api.adapters.sgp.fakes import FakeSgpProvider
from ondeline_api.adapters.sgp.router import SgpRouter
from ondeline_api.db.models.business import (
    Conversa,
    ConversaEstado,
    ConversaStatus,
    SgpProvider as SgpProviderEnum,
)
from ondeline_api.repositories.mensagem import MensagemRepo
from ondeline_api.services.llm_loop import run_turn
from ondeline_api.services.sgp_cache import SgpCacheService
from ondeline_api.tools.context import ToolContext

# Registrar tools
import ondeline_api.tools.transferir_para_humano  # noqa: F401
import ondeline_api.tools.buscar_cliente_sgp  # noqa: F401
import ondeline_api.tools.enviar_boleto  # noqa: F401


pytestmark = pytest.mark.asyncio


BASE = "http://evo.test"
INST = "hermes-wa"


def _cli_sgp() -> ClienteSgp:
    return ClienteSgp(
        provider=SgpProviderEnum.ONDELINE,
        sgp_id="42",
        nome="Joao",
        cpf_cnpj="11122233344",
        contratos=[Contrato(id="100", plano="Premium", status="ativo", cidade="SP")],
        endereco=EnderecoSgp(cidade="SP"),
        titulos=[
            Fatura(
                id="T1", valor=110, vencimento="2026-05-15", status="aberto",
                link_pdf="https://sgp/T1.pdf", codigo_pix="PIX_T1"
            )
        ],
    )


async def test_fluxo_completo_oi_cpf_boleto(db_session) -> None:
    cache_redis = FakeRedis(decode_responses=False)
    sgp_router = SgpRouter(
        primary=FakeSgpProvider(clientes={"11122233344": _cli_sgp()}),
        secondary=FakeSgpProvider(),
    )
    cache = SgpCacheService(
        redis=cache_redis,
        session=db_session,
        router=sgp_router,
        ttl_cliente=3600,
        ttl_negativo=300,
    )
    conv = Conversa(
        id=uuid4(), whatsapp="5511@s",
        estado=ConversaEstado.AGUARDA_OPCAO, status=ConversaStatus.BOT,
    )
    db_session.add(conv)
    await db_session.flush()

    # ── Turn 1: cliente 'oi' → bot pede CPF ──
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id="U1", text="Oi", media_type=None, media_url=None
    )
    await db_session.flush()
    fake1 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content="Oi! Pode me passar seu CPF?",
                tool_calls=[], tokens_used=10, finish_reason="stop",
            )
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T1"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx = ToolContext(
            session=db_session, conversa=conv, cliente=None,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out1 = await run_turn(
            ctx=ctx, provider=fake1, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert "CPF" in (out1.final_text or "")

    # ── Turn 2: cliente envia CPF → bot chama buscar_cliente_sgp → confirma ──
    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id="U2", text="11122233344", media_type=None, media_url=None
    )
    await db_session.flush()
    fake2 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[
                    ToolCall(id="c1", name="buscar_cliente_sgp", arguments={"cpf_cnpj": "11122233344"})
                ],
                tokens_used=20, finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Encontrei voce, Joao! Plano Premium ativo.",
                tool_calls=[], tokens_used=15, finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T2"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        # ctx novo: cliente ainda None, mas tool buscar_cliente_sgp vai vincular
        ctx2 = ToolContext(
            session=db_session, conversa=conv, cliente=None,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out2 = await run_turn(
            ctx=ctx2, provider=fake2, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert "Joao" in (out2.final_text or "") or "Encontrei" in (out2.final_text or "")
    assert "buscar_cliente_sgp" in out2.tool_calls_made
    await db_session.refresh(conv)
    assert conv.cliente_id is not None

    # ── Turn 3: cliente pede boleto → tool enviar_boleto → bot confirma ──
    from ondeline_api.db.models.business import Cliente
    from sqlalchemy import select
    cliente_db = (
        await db_session.execute(select(Cliente).where(Cliente.id == conv.cliente_id))
    ).scalar_one()

    await MensagemRepo(db_session).insert_inbound_or_skip(
        conversa_id=conv.id, external_id="U3", text="manda boleto", media_type=None, media_url=None
    )
    await db_session.flush()
    fake3 = FakeLLMProvider(
        responses=[
            ChatResponse(
                content=None,
                tool_calls=[ToolCall(id="c2", name="enviar_boleto", arguments={"max_boletos": 1})],
                tokens_used=18, finish_reason="tool_calls",
            ),
            ChatResponse(
                content="Enviei! 📄 Confere ai.", tool_calls=[],
                tokens_used=12, finish_reason="stop",
            ),
        ]
    )
    with respx.mock(assert_all_called=True) as router:
        # 1 sendMedia (boleto) + 1 sendText (PIX) + 1 sendText (resposta final do bot)
        router.post(f"{BASE}/message/sendMedia/{INST}").respond(200, json={"ok": True})
        router.post(f"{BASE}/message/sendText/{INST}").respond(
            200, json={"key": {"id": "OUT_T3"}}
        )
        adapter = EvolutionAdapter(base_url=BASE, instance=INST, api_key="k")
        ctx3 = ToolContext(
            session=db_session, conversa=conv, cliente=cliente_db,
            evolution=adapter, sgp_router=sgp_router, sgp_cache=cache,
        )
        out3 = await run_turn(
            ctx=ctx3, provider=fake3, model="Hermes-3",
            history_turns=12, max_iter=5, budget=None,
        )
        await adapter.aclose()
    assert "enviar_boleto" in out3.tool_calls_made
    assert out3.final_text and "Enviei" in out3.final_text
```

- [ ] **Step 19.2: Rodar**

```bash
pytest tests/test_e2e_llm_flow.py -v
```

Expected: `1 passed`.

- [ ] **Step 19.3: Commit**

```bash
cd /root/BLABLA/ondeline-v2
git add apps/api/tests/test_e2e_llm_flow.py
git commit -m "test(m4): add E2E synthetic flow (oi -> CPF -> buscar -> boleto)"
```

---

## Task 20: Smoke + CI + Tag

**Files:**
- Possibly modify: `infra/docker-compose.dev.yml` (worker ja sobe; nada novo)
- Possibly modify: `.github/workflows/ci.yml`

- [ ] **Step 20.1: Verificar Hermes alvo (precondition)**

```bash
curl -sS http://127.0.0.1:8642/v1/models | head -50 || echo "(gateway off)"
```

Expected: lista os modelos. Se Hermes-3 nao estiver listado, ajustar `HERMES_MODEL` no `.env` para o nome real e atualizar `.env.example`.

- [ ] **Step 20.2: Subir e checar logs**

```bash
cd /root/BLABLA/ondeline-v2
make dev
sleep 10
docker compose -f infra/docker-compose.dev.yml ps
docker compose -f infra/docker-compose.dev.yml logs --tail=30 worker
```

Expected: worker mostra task `llm_turn_task` registrada (`[tasks] . ondeline_api.workers.llm_turn.llm_turn_task`).

- [ ] **Step 20.3: Rodar suite completa**

```bash
cd /root/BLABLA/ondeline-v2/apps/api
. .venv/bin/activate
pytest -v
```

Expected: todos os testes M1+M2+M3+M4 verdes.

- [ ] **Step 20.4: Lint + mypy strict**

```bash
ruff check src tests
mypy src
```

Expected: limpo.

- [ ] **Step 20.5: CI**

```bash
cd /root/BLABLA/ondeline-v2
git push origin main
sleep 5
gh run list --limit 3
gh run watch
```

Expected: `completed success`.

- [ ] **Step 20.6: Tag m4-sgp-hermes-tools e push**

```bash
cd /root/BLABLA/ondeline-v2
git tag -a m4-sgp-hermes-tools -m "M4: SGP + Hermes + Tools concluido

- LLMProvider interface + HermesProvider (OpenAI-compat HTTP)
- SgpProvider interface + Ondeline + LinkNetAM + SgpRouter (try primary -> fallback)
- SgpCacheService (Redis primario + DB fallback + write-through + negative cache)
- 6 tools registradas (transferir_para_humano, consultar_planos, consultar_manutencoes,
  buscar_cliente_sgp, enviar_boleto, abrir_ordem_servico)
- Tool registry com auto-registro + JSON schema OpenAI
- LLM tool-calling loop (max_iter, budget tokens/conversa/dia, escalate fallback)
- FSM expandida (LLM_TURN action; HUMANO/AGUARDA_ATENDENTE bloqueia LLM)
- os_sequence (atomico daily counter para OS-YYYYMMDD-NNN)
- Migration 0002 (os_sequence)
- E2E sintetico verde (Oi -> CPF -> buscar_cliente_sgp -> enviar_boleto)
- ~50+ testes (unit + integration + E2E), CI verde"
git push --tags
```

- [ ] **Step 20.7: Cleanup**

```bash
cd /root/BLABLA/ondeline-v2
make down
```

---

## Definition of Done — M4

- [ ] `LLMProvider` (abstrato) + `HermesProvider` (impl) + `FakeLLMProvider` (test double)
- [ ] `HermesProvider` envia mensagens em formato OpenAI (system/user/assistant/tool com tool_calls)
- [ ] `SgpProvider` interface + `SgpOndelineProvider` + `SgpLinkNetAMProvider` + `SgpRouter` (Ondeline 1º, fallback LinkNetAM)
- [ ] `SgpCacheService` (Redis primario, DB fallback quando Redis down, write-through, negative cache 5min, invalidate)
- [ ] Tools registry: `@tool` decorator + `specs()` + `invoke()` + dedup; expomos schema OpenAI corretamente
- [ ] Tool `transferir_para_humano`: muda Conversa.status=AGUARDANDO + estado=AGUARDA_ATENDENTE
- [ ] Tool `consultar_planos`: lê de Config['planos'] ou default
- [ ] Tool `consultar_manutencoes`: filtra por cidade + janela ativa (now between inicio/fim)
- [ ] Tool `buscar_cliente_sgp`: cache hit/miss + upsert Cliente + vincula Conversa.cliente_id
- [ ] Tool `enviar_boleto`: envia ate N PDFs + PIX via EvolutionAdapter; invalida cache pos-envio
- [ ] Tool `abrir_ordem_servico`: gera código `OS-YYYYMMDD-NNN` atomico + roteia técnico por (cidade, rua) + notifica via WhatsApp
- [ ] Migration `0002_os_sequence` aplicada; `next_codigo` retorna sequencial diario testado em concorrencia
- [ ] PII mask (CPF/CNPJ/telefone/email) aplicado em logs do loop
- [ ] TokensBudget (Redis counter por conversa/dia) escala humano quando excede `LLM_MAX_TOKENS_PER_CONVERSA_DIA`
- [ ] LLM loop: 1) chama provider; 2) se text-only -> envia + persiste + sai; 3) se tool_calls -> executa tools, anexa resultados, repete; max_iter=5; transferir_para_humano sai imediato
- [ ] Loop tem fallback robusto: provider raise / max_iter / budget excedido -> envia "tive um probleminha" + escala
- [ ] FSM atualizada: HUMANO/AGUARDA_ATENDENTE bloqueia LLM; INICIO->AGUARDA_OPCAO transparente; ENCERRADA reabre
- [ ] `services/inbound.py` enfileira `llm_turn_task` (fila `llm`) em vez de `send_outbound_task` em ack
- [ ] `workers/llm_turn.py` monta provider + router + cache + adapter por task; aclose no finally
- [ ] E2E `test_e2e_llm_flow.py` verde: 3 turnos sequenciais com FakeLLM scriptado
- [ ] `make test` passa; `make lint` limpo
- [ ] CI verde no GitHub Actions
- [ ] Tag `m4-sgp-hermes-tools` criada e pushada

## Proximos passos (nao fazem parte do M4)

- M5 (Notificacoes): Celery beat + jobs de vencimento/atraso/pagamento/follow-up OS + manutencoes
- M6 (Dashboard): atendente humano efetivamente atende as conversas em status=AGUARDANDO; CRUD OS, técnicos, leads, config (incluindo planos)
- M7 (PWA tecnico): técnico recebe OS no celular, fotografa, conclui
- M8: Eval LLM rigoroso (DeepEval/ragas), endpoint /metrics Prometheus, /healthz rico, OpenTelemetry, LGPD purge
- M9: cutover

## Notas operacionais

- O `HermesProvider` precisa de `HERMES_MODEL=Hermes-3` (corrigir `.env` real). Default do M3 era `anthropic/claude-opus-4.6` — herda do scaffold mas e errado para o gateway local. Step 20.1 valida.
- Se Hermes responde com modelo diferente do esperado (ex: gateway redireciona Hermes-3 -> outra coisa), nao quebra; passamos `model` no body que o gateway aceita ou ignora.
- O `SgpCacheService` usa `hash_pii(cpf)` (HMAC com pepper) — mesma chave usada em `clientes.cpf_hash`, então DB fallback usa a mesma indexação.
- O `enviar_boleto` precisa do CPF cleartext (decrypt do `Cliente.cpf_cnpj_encrypted`) para reusar `sgp_cache.get_cliente`. Custo: 1 decrypt por chamada da tool. Aceitavel.
- `transferir_para_humano` retorna imediato no loop (nao re-chama LLM) — invariante critico, testado.
- `os_sequence` usa `INSERT ... ON CONFLICT DO UPDATE RETURNING n` que e atomico em uma round-trip — seguro sob concorrencia, sem precisar de SELECT FOR UPDATE separado.
- Sob carga alta, considerar mover `llm_turn_task` para uma fila `llm` separada com `--concurrency` propria (ex: 2). docker-compose dev por enquanto roda tudo em um worker so com `-Q default,llm,sgp,notifications`.
- O `FakeLLMProvider` usado nos testes exhausta com erro claro se exceder o numero de respostas scriptadas — facilita ver onde o loop chamou demais.
- A subscricao no Hermes consome tokens; em desenvolvimento, recomenda-se `LLM_MAX_TOKENS_PER_CONVERSA_DIA=5000` no `.env` local pra evitar custos imprevistos enquanto se itera.

