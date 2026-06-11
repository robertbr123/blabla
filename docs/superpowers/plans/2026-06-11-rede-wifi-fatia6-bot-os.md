# Rede WiFi — Fatia 6: diagnóstico no bot (LLM) + na OS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar o diagnóstico de rede (Fatia 2) pro bot (triagem de internet lenta) e pra OS (sinal + bolinha de cor pro técnico), mais o PPPoE no painel da conversa.

**Architecture:** Um helper único `qualidade_sinal` (cor). Tool LLM `consultar_rede` reusa `RedeService`. Captura best-effort do sinal ao criar OS (tool + endpoint), gravada em coluna JSONB nova, entregue na notificação WhatsApp e no `OsOut` (que o app técnico já lê). PPPoE exposto no `DiagnosticoOut`.

**Tech Stack:** FastAPI + Alembic + pytest (backend); Next.js (dashboard); Flutter (app técnico).

**Spec:** `docs/superpowers/specs/2026-06-11-rede-wifi-fatia6-bot-os-design.md`

**Convenção:** testes/ruff/mypy/build rodam no CI pós-push. Escrever em ordem TDD; NÃO rodar comandos. `git commit` por task (NO push). Branch `main`. **CI lessons:** com `from __future__ import annotations` NUNCA aspas em anotação (ruff UP037); todo import usado (F401); mypy strict roda em src+tests (tipar tudo, inclusive fakes de teste).

---

### Task 1: helper `qualidade_sinal`

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Write the failing test**

Add to `test_rede_service.py`:

```python
def test_qualidade_sinal_faixas() -> None:
    from ondeline_api.services.rede_service import qualidade_sinal
    assert qualidade_sinal(None) == ("desconhecido", "⚪")
    assert qualidade_sinal(-13.0) == ("bom", "🟢")
    assert qualidade_sinal(-25.0) == ("bom", "🟢")      # -25 inclusive = bom
    assert qualidade_sinal(-26.0) == ("atencao", "🟡")
    assert qualidade_sinal(-28.0) == ("critico", "🔴")  # < -27
    assert qualidade_sinal(-5.0) == ("critico", "🔴")   # > -8 quente demais
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_rede_service.py::test_qualidade_sinal_faixas -v`
Expected: FAIL (`qualidade_sinal` não existe).

- [ ] **Step 3: Implement (module-level in `rede_service.py`, perto do topo após os imports)**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_rede_service.py::test_qualidade_sinal_faixas -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): helper qualidade_sinal (cor por faixa de RX)"
```

---

### Task 2: PPPoE no diagnostico

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Modify: `apps/api/src/ondeline_api/api/schemas/rede.py`
- Modify: `apps/api/src/ondeline_api/api/v1/rede.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Write the failing test**

Add to `test_rede_service.py` (reusa `_dev_diag`/`_FakeGenie`/`_svc` já existentes da Fatia 2):

```python
async def test_diagnostico_inclui_pppoe(db_session: AsyncSession) -> None:
    genie = _FakeGenie(by_pppoe=_dev_diag())
    svc = _svc(db_session, genie)  # _cli_sgp() tem pppoe "rosineidesilva"
    diag = await svc.diagnostico_rede(CPF)
    assert diag.encontrada is True
    assert diag.pppoe_login == "rosineidesilva"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_rede_service.py::test_diagnostico_inclui_pppoe -v`
Expected: FAIL (`DiagnosticoRede` não tem `pppoe_login`).

- [ ] **Step 3: Implement**

(a) `rede_service.py` — `DiagnosticoRede` dataclass ganha o campo (após `device`):
```python
    pppoe_login: str | None = None
```
(b) `rede_service.py` — `diagnostico_rede`: passar o pppoe nos dois retornos:
```python
        if res.device is None:
            return DiagnosticoRede(
                encontrada=False, pppoe_login=res.pppoe, motivo="onu_nao_encontrada"
            )
        await self._genie.refresh_wan(res.device.device_id)
        return DiagnosticoRede(encontrada=True, device=res.device, pppoe_login=res.pppoe)
```
(c) `api/schemas/rede.py` — `DiagnosticoOut` ganha o campo (após `sinal`):
```python
    pppoe_login: str | None = None
```
(d) `api/v1/rede.py` — `diagnostico_out` mapper, nos dois ramos:
```python
def diagnostico_out(diag: DiagnosticoRede) -> DiagnosticoOut:
    if not diag.encontrada or diag.device is None:
        return DiagnosticoOut(
            encontrada=False, pppoe_login=diag.pppoe_login, motivo=diag.motivo
        )
    d = diag.device
    return DiagnosticoOut(
        encontrada=True,
        last_inform=d.last_inform,
        aparelhos=[
            AparelhoOut(nome=a.nome, ip=a.ip, mac=a.mac, ativo=a.ativo, interface=a.interface)
            for a in d.aparelhos
        ],
        sinal=_sinal_out(d.sinal),
        pppoe_login=diag.pppoe_login,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_rede_service.py -k "diagnostico" -v`
Expected: PASS (o novo + os existentes da Fatia 2).

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/src/ondeline_api/api/schemas/rede.py apps/api/src/ondeline_api/api/v1/rede.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): pppoe_login no DiagnosticoOut (painel mostra o PPPoE)"
```

---

### Task 3: tool `consultar_rede`

**Files:**
- Create: `apps/api/src/ondeline_api/tools/consultar_rede.py`
- Modify: `apps/api/src/ondeline_api/workers/llm_turn.py`
- Test: `apps/api/tests/test_tool_consultar_rede.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_tool_consultar_rede.py`:

```python
"""Tool consultar_rede: aparelhos + sinal pro bot triar internet lenta."""
from __future__ import annotations

from typing import Any

import pytest
from ondeline_api.db.models.business import Cliente
from ondeline_api.db.crypto import encrypt_pii, hash_pii

pytestmark = pytest.mark.asyncio


def _ctx(cliente: Cliente | None) -> Any:
    class _Ctx:
        def __init__(self) -> None:
            self.session = None
            self.conversa = None
            self.cliente = cliente
            self.evolution = None
            self.sgp_router = None
            self.sgp_cache = None
    return _Ctx()


async def test_consultar_rede_sem_cliente() -> None:
    from ondeline_api.tools.consultar_rede import consultar_rede
    out = await consultar_rede(_ctx(None))
    assert out["encontrada"] is False
    assert out["motivo"] == "cliente_nao_identificado"


async def test_payload_consulta_formata_aparelhos_e_sinal() -> None:
    # Testa o nucleo (sem GenieACS real) via um fake RedeService.
    from ondeline_api.adapters.genieacs.base import Aparelho, GenieAcsDevice, SinalFibra
    from ondeline_api.services.rede_service import DiagnosticoRede
    from ondeline_api.tools.consultar_rede import _payload_consulta

    class _FakeRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            dev = GenieAcsDevice(
                device_id="X", online=True,
                aparelhos=[Aparelho(nome="A", ip="1", mac="m1", ativo=True),
                           Aparelho(nome="B", ip="2", mac="m2", ativo=True)],
                sinal=SinalFibra(rx_power=-13.0),
            )
            return DiagnosticoRede(encontrada=True, device=dev)

    out = await _payload_consulta(_FakeRede(), "04099889289")
    assert out["encontrada"] is True
    assert out["aparelhos_conectados"] == 2
    assert out["sinal"]["qualidade"] == "bom"
    assert out["sinal"]["emoji"] == "🟢"
    assert out["sinal"]["rx_power"] == -13.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_tool_consultar_rede.py -v`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implement `tools/consultar_rede.py`**

```python
"""Tool: consulta a rede do cliente (aparelhos conectados + sinal da fibra).

Usada pelo bot quando o cliente reclama de internet lenta/instavel. Reusa o
RedeService (Fatia 2). Best-effort: GenieACS fora -> retorno amigavel, nunca
quebra o loop do LLM.
"""
from __future__ import annotations

from typing import Any, Protocol

from ondeline_api.adapters.genieacs.base import GenieAcsUnavailableError
from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.services.rede_service import (
    DiagnosticoRede,
    RedeService,
    qualidade_sinal,
)
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}


class _RedeProto(Protocol):
    async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede: ...


async def _payload_consulta(rede: _RedeProto, cpf: str) -> dict[str, Any]:
    diag = await rede.diagnostico_rede(cpf)
    if not diag.encontrada or diag.device is None:
        return {"encontrada": False, "motivo": diag.motivo}
    d = diag.device
    rx = d.sinal.rx_power if d.sinal else None
    label, emoji = qualidade_sinal(rx)
    return {
        "encontrada": True,
        "online": d.online,
        "aparelhos_conectados": len(d.aparelhos),
        "sinal": {"rx_power": rx, "qualidade": label, "emoji": emoji},
    }


@tool(
    name="consultar_rede",
    description=(
        "Consulta a rede do cliente vinculado a esta conversa: quantos aparelhos "
        "estao conectados agora e a qualidade do sinal da fibra. Use quando o "
        "cliente reclamar de internet lenta, caindo ou instavel."
    ),
    parameters=SCHEMA,
)
async def consultar_rede(ctx: ToolContext) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"encontrada": False, "motivo": "cliente_nao_identificado"}
    cpf = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
    genie = GenieAcsClient(base_url=get_settings().genieacs_url)
    rede = RedeService(session=ctx.session, genieacs=genie, sgp_cache=ctx.sgp_cache)
    try:
        return await _payload_consulta(rede, cpf)
    except GenieAcsUnavailableError:
        return {"erro": "indisponivel"}
    finally:
        await genie.aclose()
```

- [ ] **Step 4: Registrar a tool (import em `workers/llm_turn.py`)**

Em `workers/llm_turn.py`, junto dos outros `import ondeline_api.tools.<x>` (linhas ~10-17), adicione:
```python
import ondeline_api.tools.consultar_rede  # noqa: F401
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_tool_consultar_rede.py -v`
Expected: PASS (2 testes).

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/tools/consultar_rede.py apps/api/src/ondeline_api/workers/llm_turn.py apps/api/tests/test_tool_consultar_rede.py
git commit -m "feat(rede): tool consultar_rede (aparelhos + sinal pro bot)"
```

---

### Task 4: instrução no system prompt (bot triagem)

**Files:**
- Modify: `apps/api/src/ondeline_api/services/llm_loop.py`

- [ ] **Step 1: Adicionar a instrução ao `SYSTEM_PROMPT`**

No `SYSTEM_PROMPT` (começa na linha 46), insira um bloco novo logo APÓS o bloco que termina com "...NUNCA invente valor.\n\n" (fim da seção "APOS IDENTIFICAR O CLIENTE"). Adicione como string concatenada (mesmo estilo das outras linhas):

```python
    "INTERNET LENTA / INSTAVEL / CAINDO (cliente ja identificado):\n"
    "- Use a tool consultar_rede.\n"
    "- Reporte de forma NATURAL quantos aparelhos estao conectados e como esta o "
    "sinal. NUNCA mostre campos crus (rx_power etc.) — traduza ('seu sinal esta otimo/"
    "no limite/fraco').\n"
    "- Se sinal 'critico' (🔴): explique que provavelmente e o sinal da fibra e "
    "OFERECA abrir um chamado tecnico. So chame abrir_ordem_servico se o cliente "
    "CONFIRMAR.\n"
    "- Se muitos aparelhos conectados (>10): comente que pode ser congestionamento "
    "da rede dele (sugira desligar aparelhos sem uso).\n"
    "- Se a tool retornar encontrada=false: nao invente; siga o atendimento normal.\n\n"
```

- [ ] **Step 2: Verificar se prod usa PromptVariant (nota de deploy)**

Run (na máquina de deploy, read-only): `docker exec blabla-postgres psql -U ondeline -d ondeline -c "select nome, ativo, trafego_pct, canal_slug from prompt_variants where ativo = true;"`
- Se **não houver variante ativa** → o `SYSTEM_PROMPT` (editado acima) é o que roda. Pronto.
- Se **houver variante ativa cobrindo o canal de suporte** → a instrução também precisa ser adicionada ao `system_prompt` daquela variante no DB (a edição em código não afeta os clientes que caem na variante). Anotar como follow-up pós-deploy; NÃO bloqueia esta task.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/services/llm_loop.py
git commit -m "feat(rede): instrucao de triagem de internet lenta no system prompt"
```

---

### Task 5: coluna `sinal` na OS + OsOut + repo (Parte C fundação)

**Files:**
- Modify: `apps/api/src/ondeline_api/db/models/business.py`
- Create: `apps/api/alembic/versions/0047_os_sinal.py`
- Modify: `apps/api/src/ondeline_api/api/schemas/os.py`
- Modify: `apps/api/src/ondeline_api/repositories/ordem_servico.py`

- [ ] **Step 1: Model — adicionar a coluna**

Em `db/models/business.py`, em `class OrdemServico`, após `nome_sgp` (linha 447):
```python
    sinal: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
```
(`JSONB`, `Any`, `Mapped`, `mapped_column` já importados no arquivo.)

- [ ] **Step 2: Migração**

Create `apps/api/alembic/versions/0047_os_sinal.py`:
```python
"""ordens_servico: coluna sinal (snapshot optico no momento da OS).

Revision ID: 0047_os_sinal
Revises: 0046_rede_wifi_pedido_tipo
Create Date: 2026-06-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047_os_sinal"
down_revision: str | None = "0046_rede_wifi_pedido_tipo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ordens_servico",
        sa.Column("sinal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ordens_servico", "sinal")
```

- [ ] **Step 3: `OsOut` ganha o campo**

Em `api/schemas/os.py`, em `class OsOut`, adicione (junto dos outros campos opcionais):
```python
    sinal: dict[str, Any] | None = None
```
(`Any` já importado no arquivo.)

- [ ] **Step 4: `OrdemServicoRepo.create` aceita `sinal`**

Em `repositories/ordem_servico.py`, no método `create`, adicione o param e passe ao construtor:
```python
    async def create(
        self,
        *,
        codigo: str,
        cliente_id: UUID | None,
        tecnico_id: UUID | None,
        problema: str,
        endereco: str,
        plano: str | None = None,
        pppoe_login: str | None = None,
        pppoe_senha: str | None = None,
        sinal: dict[str, Any] | None = None,
    ) -> OrdemServico:
        os_ = OrdemServico(
            codigo=codigo,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            problema=problema,
            endereco=endereco,
            status=OsStatus.PENDENTE,
            plano=plano,
            pppoe_login=pppoe_login,
            pppoe_senha=pppoe_senha,
            sinal=sinal,
        )
        self._session.add(os_)
        await self._session.flush()
        return os_
```
(`Any` já importado no topo de `ordem_servico.py`.)

- [ ] **Step 5: Verificar (deploy)**

Run: `cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
Expected: sobe/desce sem erro.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/ondeline_api/db/models/business.py apps/api/alembic/versions/0047_os_sinal.py apps/api/src/ondeline_api/api/schemas/os.py apps/api/src/ondeline_api/repositories/ordem_servico.py
git commit -m "feat(os): coluna sinal (JSONB) + OsOut + repo.create aceita sinal + migracao 0047"
```

---

### Task 6: helper `snapshot_sinal`

**Files:**
- Modify: `apps/api/src/ondeline_api/services/rede_service.py`
- Test: `apps/api/tests/test_rede_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_snapshot_sinal_ok_e_best_effort(db_session: AsyncSession) -> None:
    from ondeline_api.adapters.genieacs.base import (
        GenieAcsUnavailableError, SinalFibra,
    )
    from ondeline_api.services.rede_service import DiagnosticoRede, snapshot_sinal
    from ondeline_api.adapters.genieacs.base import GenieAcsDevice

    class _OkRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            dev = GenieAcsDevice(device_id="X", sinal=SinalFibra(rx_power=-26.0, tx_power=2.0, status_gpon="Up"))
            return DiagnosticoRede(encontrada=True, device=dev)

    snap = await snapshot_sinal(_OkRede(), "04099889289")
    assert snap is not None
    assert snap["rx_power"] == -26.0
    assert snap["qualidade"] == "atencao"

    class _DownRede:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            raise GenieAcsUnavailableError("fora")

    assert await snapshot_sinal(_DownRede(), "04099889289") is None  # best-effort

    class _SemOnu:
        async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede:
            return DiagnosticoRede(encontrada=False, motivo="onu_nao_encontrada")

    assert await snapshot_sinal(_SemOnu(), "04099889289") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_rede_service.py::test_snapshot_sinal_ok_e_best_effort -v`
Expected: FAIL (`snapshot_sinal` não existe).

- [ ] **Step 3: Implement (module-level em `rede_service.py`)**

Adicione perto de `qualidade_sinal`. Importe `GenieAcsUnavailableError` no topo do arquivo se ainda não estiver (verifique; é de `ondeline_api.adapters.genieacs.base`).

```python
class _DiagProto(Protocol):
    async def diagnostico_rede(self, cpf: str) -> "DiagnosticoRede": ...


async def snapshot_sinal(rede: _DiagProto, cpf: str) -> dict[str, Any] | None:
    """Snapshot do sinal optico pra gravar numa OS. Best-effort: GenieACS fora
    ou sem ONU -> None (a OS e criada mesmo assim)."""
    try:
        diag = await rede.diagnostico_rede(cpf)
    except GenieAcsUnavailableError:
        return None
    if not diag.encontrada or diag.device is None or diag.device.sinal is None:
        return None
    s = diag.device.sinal
    return {
        "rx_power": s.rx_power,
        "tx_power": s.tx_power,
        "status_gpon": s.status_gpon,
        "qualidade": qualidade_sinal(s.rx_power)[0],
    }
```
NOTE: a anotação `"DiagnosticoRede"` no Protocol — como o arquivo tem `from __future__ import annotations`, escreva SEM aspas: `async def diagnostico_rede(self, cpf: str) -> DiagnosticoRede: ...` (UP037). `Protocol`, `Any` precisam estar importados de `typing` (verifique; adicione se faltar). `DiagnosticoRede` é definido no mesmo arquivo (acima ou abaixo — com `__future__` a forward-ref resolve).

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_rede_service.py::test_snapshot_sinal_ok_e_best_effort -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/rede_service.py apps/api/tests/test_rede_service.py
git commit -m "feat(rede): helper snapshot_sinal (best-effort pra gravar na OS)"
```

---

### Task 7: captura de sinal no tool `abrir_ordem_servico`

**Files:**
- Modify: `apps/api/src/ondeline_api/tools/abrir_ordem_servico.py`
- Test: `apps/api/tests/test_tool_abrir_os.py` (criar se não existir; senão adicionar)

- [ ] **Step 1: Write the failing test**

Crie/append `apps/api/tests/test_tool_abrir_os.py`. O teste verifica que, ao abrir OS, o snapshot do sinal é gravado e a notificação inclui a linha. Como `abrir_ordem_servico` constrói o `GenieAcsClient`/RedeService internamente, mocamos via monkeypatch do `snapshot_sinal` que a tool chama:

```python
"""abrir_ordem_servico: grava snapshot de sinal + linha na notificacao."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from ondeline_api.db.crypto import encrypt_pii, hash_pii
from ondeline_api.db.models.business import Cliente, Conversa, OrdemServico
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

CPF = "04099889289"


class _FakeWpp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, to: str, text: str) -> None:
        self.sent.append((to, text))


async def test_abrir_os_grava_sinal_e_notifica(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ondeline_api.tools.abrir_ordem_servico as mod

    # _capturar_sinal mockado por inteiro (evita GenieACS/get_settings no teste)
    async def fake_cap(ctx: Any) -> dict[str, Any]:
        return {"rx_power": -29.0, "tx_power": 2.0, "status_gpon": "Up", "qualidade": "critico"}
    monkeypatch.setattr(mod, "_capturar_sinal", fake_cap)
    # endereco do cadastro mockado (evita SGP real)
    async def fake_end(ctx: Any) -> tuple[str, str, str]:
        return ("Rua X, 1 — Centro — Manaus/AM", "Rua X", "Manaus")
    monkeypatch.setattr(mod, "_resolve_endereco_do_cadastro", fake_end)

    cli = Cliente(cpf_cnpj_encrypted=encrypt_pii(CPF), cpf_hash=hash_pii(CPF),
                  nome_encrypted=encrypt_pii("Fulano"), whatsapp="5599@c.us")
    db_session.add(cli)
    await db_session.flush()
    conv = Conversa(whatsapp="5599@c.us", cliente_id=cli.id)
    db_session.add(conv)
    await db_session.flush()

    wpp = _FakeWpp()

    class _Ctx:
        session = db_session
        conversa = conv
        cliente = cli
        evolution = wpp
        sgp_router = None
        sgp_cache = None
        redis = None

    # tecnico opcional — sem tecnico, nao notifica, mas sinal e gravado.
    out = await mod.abrir_ordem_servico(_Ctx(), problema="internet lenta")
    assert out["ok"] is True
    os_ = (await db_session.execute(select(OrdemServico))).scalars().first()
    assert os_ is not None
    assert os_.sinal is not None
    assert os_.sinal["qualidade"] == "critico"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_tool_abrir_os.py -v`
Expected: FAIL (`mod.snapshot_sinal` não existe / sinal não gravado).

- [ ] **Step 3: Implement em `abrir_ordem_servico.py`**

(a) Imports novos (topo):
```python
from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.config import get_settings
from ondeline_api.services.rede_service import RedeService, qualidade_sinal, snapshot_sinal
```
(b) Função módulo-level `_capturar_sinal` (extraída pra ser mockável no teste — assim o teste não toca em `get_settings`/GenieACS). Coloque acima da `abrir_ordem_servico`:
```python
async def _capturar_sinal(ctx: ToolContext) -> dict[str, Any] | None:
    """Snapshot best-effort do sinal pra gravar na OS. Nunca propaga erro."""
    if ctx.cliente is None:
        return None
    try:
        cpf_cli = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
        genie = GenieAcsClient(base_url=get_settings().genieacs_url)
        try:
            rede = RedeService(session=ctx.session, genieacs=genie, sgp_cache=ctx.sgp_cache)
            return await snapshot_sinal(rede, cpf_cli)
        finally:
            await genie.aclose()
    except Exception as e:  # nunca bloqueia a criacao da OS
        log.warning("abrir_os.sinal_snapshot_falhou", error=str(e))
        return None
```
(c) Dentro de `abrir_ordem_servico`, antes do `OrdemServicoRepo(...).create(...)`:
```python
    sinal_snap = await _capturar_sinal(ctx)
```
(d) Passe `sinal=sinal_snap` no `.create(...)`:
```python
    os_ = await OrdemServicoRepo(ctx.session).create(
        codigo=codigo,
        cliente_id=ctx.cliente.id,
        tecnico_id=tecnico.id if tecnico else None,
        problema=problema,
        endereco=endereco_final,
        sinal=sinal_snap,
    )
```
(e) Na mensagem do técnico (`msg = (...)`), adicione a linha de sinal antes do "Quando concluir":
```python
        linha_sinal = ""
        if sinal_snap and sinal_snap.get("rx_power") is not None:
            _, emoji = qualidade_sinal(sinal_snap["rx_power"])
            linha_sinal = f"*Sinal:* {emoji} {sinal_snap['rx_power']} dBm\n"
        msg = (
            f"🔧 *Nova OS atribuída a você*\n\n"
            f"*Código:* {codigo}\n"
            f"*Cliente:* {nome_cliente}\n"
            f"*WhatsApp:* {wpp_fmt}\n"
            f"*Endereço:* {endereco_final}\n"
            f"*Problema:* {problema}\n"
            f"{linha_sinal}\n"
            f"Quando concluir, mande no chat:\n"
            f"_CONCLUIR {codigo}_"
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_tool_abrir_os.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/tools/abrir_ordem_servico.py apps/api/tests/test_tool_abrir_os.py
git commit -m "feat(os): tool abrir_ordem_servico grava snapshot de sinal + linha na notificacao"
```

---

### Task 8: captura de sinal no `POST /api/v1/os`

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/ordens_servico.py`
- Test: `apps/api/tests/test_v1_os.py` (adicionar; criar se não existir)

- [ ] **Step 1: Write the failing test**

Adicione um teste que cria uma OS via `POST /api/v1/os` com um `_FakeService` (override de `get_rede_service`) e um Cliente real, e confere que `sinal` foi gravado. Use o padrão de override de `tests/test_v1_conversas_rede.py` (db_session/redis/get_rede_service). Esqueleto:

```python
async def test_create_os_grava_sinal(db_session, redis_client) -> None:
    from ondeline_api.adapters.genieacs.base import GenieAcsDevice, SinalFibra
    from ondeline_api.api.v1.rede import get_rede_service
    from ondeline_api.db.crypto import encrypt_pii, hash_pii
    from ondeline_api.db.models.business import Cliente, OrdemServico
    from ondeline_api.db.models.identity import Role
    from ondeline_api.services.rede_service import DiagnosticoRede
    from sqlalchemy import select

    class _FakeRede:
        async def diagnostico_rede(self, cpf, serial=None):
            dev = GenieAcsDevice(device_id="X", sinal=SinalFibra(rx_power=-13.0, status_gpon="Up"))
            return DiagnosticoRede(encontrada=True, device=dev)

    # ... cria Cliente (encrypt CPF), Tecnico ativo, admin user + login,
    # override get_db/get_redis/get_rede_service (yield _FakeRede()),
    # POST /api/v1/os com {tecnico_id, problema, endereco, cliente_id},
    # assert 201 + body["sinal"]["qualidade"] == "bom" + a OS no banco tem sinal.
```
(O implementer deve completar o teste seguindo o padrão de `test_v1_conversas_rede.py` para fixtures/login/override, e do `tests/test_v1_os.py` existente para criar Técnico/admin. Mantenha os asserts: status 201, `body["sinal"]["qualidade"]=="bom"`, e a row no banco com `sinal` não-nulo.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && pytest tests/test_v1_os.py -k sinal -v`
Expected: FAIL (sinal não capturado).

- [ ] **Step 3: Implement em `ordens_servico.py` `create_os`**

(a) Imports (topo): `from ondeline_api.api.v1.rede import get_rede_service`, `from ondeline_api.services.rede_service import RedeService, qualidade_sinal, snapshot_sinal`, `from ondeline_api.db.crypto import decrypt_pii`, `from ondeline_api.db.models.business import Cliente` (se não importados), `from sqlalchemy import select` (se não), `import structlog` + `log = structlog.get_logger(__name__)` (se não houver).

(b) Injetar o RedeService na assinatura:
```python
async def create_os(
    body: OsCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    rede: Annotated[RedeService, Depends(get_rede_service)],
) -> OsOut:
```

(c) Antes do `repo.create(...)`, capturar o sinal best-effort a partir do cliente:
```python
    sinal_snap: dict[str, Any] | None = None
    if body.cliente_id is not None:
        try:
            cli = (await session.execute(
                select(Cliente).where(Cliente.id == body.cliente_id)
            )).scalar_one_or_none()
            if cli is not None and cli.cpf_cnpj_encrypted:
                sinal_snap = await snapshot_sinal(rede, decrypt_pii(cli.cpf_cnpj_encrypted))
        except Exception as e:  # nunca bloqueia a criacao da OS
            log.warning("create_os.sinal_snapshot_falhou", error=str(e))
```
(`Any` precisa estar importado no arquivo — adicione `from typing import Any` se faltar.)

(d) Passar `sinal=sinal_snap` no `repo.create(...)`.

(e) Na mensagem do técnico (`msg += ...`), antes da linha de "Problema", quando há sinal:
```python
        if sinal_snap and sinal_snap.get("rx_power") is not None:
            _, emoji = qualidade_sinal(sinal_snap["rx_power"])
            msg += f"📶 *Sinal:* {emoji} {sinal_snap['rx_power']} dBm\n"
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/api && pytest tests/test_v1_os.py -k sinal -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/api/v1/ordens_servico.py apps/api/tests/test_v1_os.py
git commit -m "feat(os): POST /os captura sinal best-effort + linha na notificacao"
```

---

### Task 9: PPPoE no painel (dashboard)

**Files:**
- Modify: `apps/dashboard/lib/api/types.ts`
- Modify: `apps/dashboard/components/conversa-rede-panel.tsx`

- [ ] **Step 1: Tipo**

Em `types.ts`, na interface `RedeDiagnostico`, adicione:
```typescript
  pppoe_login: string | null
```

- [ ] **Step 2: Mostrar no painel**

Em `conversa-rede-panel.tsx`, na seção do sinal (dentro do bloco `else` do `if (d.sinal == null)`, ou logo após o bloco do sinal), adicione uma linha mostrando o PPPoE quando presente:
```tsx
        {d.pppoe_login && <p>PPPoE: {d.pppoe_login}</p>}
```
(coloque dentro do `<div>` da seção "Sinal da fibra", após o `<p>Uptime: ...</p>`, ou logo antes do fechamento do bloco do sinal — onde fizer sentido visual.)

- [ ] **Step 3: Verificar (typecheck)**

Run: `cd apps/dashboard && ./node_modules/.bin/tsc --noEmit`
Expected: sem erros.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/lib/api/types.ts apps/dashboard/components/conversa-rede-panel.tsx
git commit -m "feat(rede/dashboard): mostra PPPoE do cliente no painel da conversa"
```

---

### Task 10: sinal na tela de detalhe da OS (app técnico Flutter)

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/os/os_detail_screen.dart`

- [ ] **Step 1: Ler `sinal` do map e renderizar a bolinha**

A tela lê a OS de um `Map<String, dynamic>` (`os`). No `_Body` (linha ~50), onde os campos são extraídos (`os.readString('problema')` etc.), e na `_ContextSection` que renderiza o bloco de conexão, adicione a exibição do sinal.

(a) Helper de cor no topo do arquivo (após os imports, fora de classe):
```dart
Color _corSinal(num? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}
```

(b) No `_Body.build`, extraia o sinal do map (logo após os outros `os.read...`):
```dart
    final sinal = os['sinal'] as Map<String, dynamic>?;
    final rx = sinal == null ? null : sinal['rx_power'] as num?;
```

(c) Passe `rx`/`sinal` pra `_ContextSection` (adicione os params no construtor e na chamada) e renderize, dentro do bloco de conexão/contexto, quando `sinal != null`:
```dart
            if (sinal != null)
              Row(children: [
                Icon(Icons.circle, size: 12, color: _corSinal(rx)),
                const SizedBox(width: 8),
                Text('Sinal: ${rx ?? '—'} dBm'
                    '${sinal['status_gpon'] != null ? ' · ${sinal['status_gpon']}' : ''}'),
              ]),
```
(Posicione junto do `_ConnectionBlock` — onde plano/login/senha aparecem — pra ficar no contexto técnico. Ajuste a passagem de params de `_ContextSection`/`_ConnectionBlock` conforme a estrutura: adicione `final num? rx; final Map<String,dynamic>? sinal;` e renderize a Row acima quando `sinal != null`.)

- [ ] **Step 2: Verificar análise estática**

Run: `cd apps/tecnico-mobile && flutter analyze` (na máquina de deploy)
Expected: sem issues novos.

- [ ] **Step 3: Commit**

```bash
git add apps/tecnico-mobile/lib/features/os/os_detail_screen.dart
git commit -m "feat(os/app): bolinha de sinal na tela de detalhe da OS do tecnico"
```

---

## Notas de deploy / follow-up
- **Prompt em prod:** se houver `PromptVariant` ativa cobrindo o suporte, adicionar a instrução de triagem ao `system_prompt` daquela variante no DB (Task 4, Step 2).
- **App técnico:** rebuild/redistribuir o `tecnico-mobile` pra ver a bolinha na OS (Watchtower não atualiza apps). Offline o sinal não aparece (vem só do fetch da API) — degradação aceitável.
- **HG6145D:** path óptico herdado da Fatia 2 — onde o sinal não é lido, a OS grava `sinal=null` e o bot reporta só aparelhos.
- **Snapshot na criação da OS** adiciona 1 chamada ao GenieACS (best-effort, engolida se falhar) — não bloqueia a OS.
