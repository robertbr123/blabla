# Bot Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar toggle on/off do bot WhatsApp no painel de configurações, sem restart de container.

**Architecture:** Guard no início de `process_inbound_message` consulta `config.bot.ativo` via `ConfigRepo` — se `False` explícito, persiste a mensagem mas retorna `skipped_reason="bot_desativado"` antes de qualquer FSM/LLM. Frontend usa os endpoints genéricos de config já existentes (`GET/PUT /api/v1/config/bot.ativo`) e um Switch shadcn/ui instalado na task 2.

**Tech Stack:** Python / SQLAlchemy async (backend), Next.js 15 / React 19 / @radix-ui/react-switch (frontend), pytest-asyncio (testes)

---

## File Map

| Ação | Arquivo |
|------|---------|
| Modify | `apps/api/src/ondeline_api/services/inbound.py` |
| Modify | `apps/api/tests/test_inbound_service.py` |
| Create | `apps/dashboard/components/ui/switch.tsx` |
| Create | `apps/dashboard/components/bot-toggle.tsx` |
| Modify | `apps/dashboard/app/(admin)/config/page.tsx` |

---

## Task 1: Backend — guard bot toggle em `inbound.py` (TDD)

**Files:**
- Modify: `apps/api/src/ondeline_api/services/inbound.py:110-123`
- Modify: `apps/api/tests/test_inbound_service.py` (adicionar testes + FakeConfigSession)

- [ ] **Step 1: Adicionar `FakeConfigSession` e escrever os 3 testes com falha esperada**

Adicione ao final das definições de fakes em `apps/api/tests/test_inbound_service.py`, depois da classe `FakeOutboundQueue` (linha ~98) e antes dos tests:

```python
# ── FakeConfigSession ─────────────────────────────────────────


class _FakeScalar:
    def __init__(self, value: Any) -> None:
        self._v = value

    def scalar_one_or_none(self) -> Any:
        return self._v


class FakeConfigSession:
    """Fake AsyncSession suficiente para ConfigRepo.get('bot.ativo')."""

    def __init__(self, bot_ativo: Any = True) -> None:
        self._bot_ativo = bot_ativo

    async def execute(self, stmt: Any) -> _FakeScalar:  # noqa: ARG002
        return _FakeScalar(self._bot_ativo)
```

Adicione o import no topo do arquivo (junto com os demais imports):
```python
from typing import Any
```

Adicione os testes depois do último teste existente:

```python
async def test_bot_desativado_persiste_e_retorna_skipped() -> None:
    """Bot desativado: mensagem é salva mas retorna skipped_reason=bot_desativado."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=False),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason == "bot_desativado"
    assert out.persisted is True
    assert out.duplicate is False
    assert out.escalated is False
    assert len(fake_msgs.inserted) == 1
    assert fake_out.sent == []
    assert fake_out.llm_turns == []


async def test_bot_ativo_true_processa_normalmente() -> None:
    """Bot ativo (value=True): fluxo normal passa pela FSM."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=True),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason is None
    assert out.persisted is True
    assert len(fake_out.llm_turns) == 1


async def test_bot_ativo_none_processa_normalmente() -> None:
    """Bot ativo implícito (chave ausente, value=None): default é ativo."""
    fake_msgs = FakeMensagemRepo()
    fake_out = FakeOutboundQueue()
    deps = InboundDeps(
        conversas=FakeConversaRepo(),
        mensagens=fake_msgs,
        outbound=fake_out,
        ack_text="ACK!",
        session=FakeConfigSession(bot_ativo=None),
    )
    out = await process_inbound_message(_evt(), deps)
    assert out.skipped_reason is None
    assert out.persisted is True
    assert len(fake_out.llm_turns) == 1
```

- [ ] **Step 2: Rodar os testes novos e verificar que falham**

```bash
cd apps/api && .venv/bin/pytest tests/test_inbound_service.py::test_bot_desativado_persiste_e_retorna_skipped tests/test_inbound_service.py::test_bot_ativo_true_processa_normalmente tests/test_inbound_service.py::test_bot_ativo_none_processa_normalmente -v
```

Esperado: 3 × FAILED (função não encontra o `skipped_reason` correto porque o guard ainda não existe)

- [ ] **Step 3: Implementar o guard em `services/inbound.py`**

Adicione o import de `ConfigRepo` ao bloco de imports do arquivo (logo após o import de `InboundEvent, InboundKind`):

```python
from ondeline_api.repositories.config import ConfigRepo
```

Insira o bloco do guard logo **depois** dos três early-returns (after line ~122, `if evt.kind is InboundKind.TEXT and not evt.text`) e **antes** de `conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)`:

```python
    if deps.session is not None:
        bot_ativo = await ConfigRepo(deps.session).get("bot.ativo")
        if bot_ativo is False:
            conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)
            await deps.mensagens.insert_inbound_or_skip(
                conversa_id=conversa.id,
                external_id=evt.external_id,
                text=evt.text,
                media_type=evt.kind.value if evt.kind in _MEDIA_KINDS else None,
                media_url=None,
            )
            return InboundResult(
                conversa_id=conversa.id,
                persisted=True,
                duplicate=False,
                escalated=False,
                skipped_reason="bot_desativado",
            )
```

O trecho resultante ao redor da inserção deve ficar assim (para referência de contexto):

```python
    if evt.kind is InboundKind.TEXT and not evt.text:
        return InboundResult(
            conversa_id=None, persisted=False, duplicate=False, escalated=False, skipped_reason="empty_text"
        )

    if deps.session is not None:
        bot_ativo = await ConfigRepo(deps.session).get("bot.ativo")
        if bot_ativo is False:
            conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)
            await deps.mensagens.insert_inbound_or_skip(
                conversa_id=conversa.id,
                external_id=evt.external_id,
                text=evt.text,
                media_type=evt.kind.value if evt.kind in _MEDIA_KINDS else None,
                media_url=None,
            )
            return InboundResult(
                conversa_id=conversa.id,
                persisted=True,
                duplicate=False,
                escalated=False,
                skipped_reason="bot_desativado",
            )

    conversa = await deps.conversas.get_or_create_by_whatsapp(evt.jid)
```

- [ ] **Step 4: Rodar toda a suite do serviço e verificar que passa**

```bash
cd apps/api && .venv/bin/pytest tests/test_inbound_service.py -v
```

Esperado: todos os testes PASS (incluindo os 3 novos e os anteriores inalterados)

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/ondeline_api/services/inbound.py apps/api/tests/test_inbound_service.py
git commit -m "feat(bot): guard toggle bot.ativo em process_inbound_message"
```

---

## Task 2: Frontend — Switch component + BotToggle card

**Files:**
- Create: `apps/dashboard/components/ui/switch.tsx`
- Create: `apps/dashboard/components/bot-toggle.tsx`
- Modify: `apps/dashboard/app/(admin)/config/page.tsx`

- [ ] **Step 1: Instalar `@radix-ui/react-switch`**

```bash
cd apps/dashboard && npm install @radix-ui/react-switch
```

Esperado: `added 1 package` (ou similar)

- [ ] **Step 2: Criar `components/ui/switch.tsx`**

Crie o arquivo `apps/dashboard/components/ui/switch.tsx` com o conteúdo:

```tsx
'use client'
import * as SwitchPrimitives from '@radix-ui/react-switch'
import { cn } from '@/lib/utils'

export function Switch({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>) {
  return (
    <SwitchPrimitives.Root
      className={cn(
        'peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'data-[state=checked]:bg-primary data-[state=unchecked]:bg-input',
        className,
      )}
      {...props}
    >
      <SwitchPrimitives.Thumb
        className={cn(
          'pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform',
          'data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0',
        )}
      />
    </SwitchPrimitives.Root>
  )
}
```

- [ ] **Step 3: Criar `components/bot-toggle.tsx`**

Crie o arquivo `apps/dashboard/components/bot-toggle.tsx`:

```tsx
'use client'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useConfigKey, useSetConfig } from '@/lib/api/queries'

const CONFIG_KEY = 'bot.ativo'

export function BotToggle() {
  const cfg = useConfigKey(CONFIG_KEY)
  const setConfig = useSetConfig()
  const [checked, setChecked] = useState(true)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cfg.data !== undefined) {
      // Regra: None (chave ausente/404) ou true → ativo. Só false → desativado.
      setChecked(cfg.data.value !== false)
    }
  }, [cfg.data])

  // Chave ausente no banco → 404 → bot está ativo (default implícito)
  const notFound = cfg.error && (cfg.error as { status?: number }).status === 404
  const loading = cfg.isLoading && !notFound

  async function handleToggle(value: boolean) {
    setChecked(value)
    setStatus(null)
    setError(null)
    try {
      await setConfig.mutateAsync({ key: CONFIG_KEY, value })
      setStatus(value ? 'Bot ativado.' : 'Bot desativado.')
    } catch (e) {
      setChecked(!value)
      setError(e instanceof Error ? e.message : 'Falha ao salvar')
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Bot WhatsApp</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <p className="text-xs text-muted-foreground">Carregando…</p>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="bot-toggle">Bot ativo</Label>
                <p className="text-xs text-muted-foreground">
                  Quando desativado, mensagens são salvas mas o bot não responde automaticamente.
                </p>
              </div>
              <Switch
                id="bot-toggle"
                checked={checked}
                onCheckedChange={handleToggle}
                disabled={setConfig.isPending}
              />
            </div>
            {status && <p className="text-xs text-emerald-600">{status}</p>}
            {error && <p className="text-xs text-destructive">{error}</p>}
          </>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Inserir `BotToggle` na página de configurações acima do SGP**

Edite `apps/dashboard/app/(admin)/config/page.tsx`:

```tsx
import { BotToggle } from '@/components/bot-toggle'
import { ConfigEditor } from '@/components/config-editor'
import { SgpConfigEditor } from '@/components/sgp-config-editor'

export default function ConfigPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <p className="text-sm text-muted-foreground">
          Editor de chaves de configuração (admin only)
        </p>
      </div>
      <BotToggle />
      <SgpConfigEditor />
      <div>
        <h2 className="text-lg font-semibold">Editor genérico (k/v)</h2>
        <p className="text-sm text-muted-foreground mb-3">
          Qualquer chave em <code>config</code> — JSON bruto.
        </p>
        <ConfigEditor />
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Verificar tipos com TypeScript**

```bash
cd apps/dashboard && npm run typecheck
```

Esperado: sem erros

- [ ] **Step 6: Commit**

```bash
cd apps/dashboard && git add components/ui/switch.tsx components/bot-toggle.tsx app/(admin)/config/page.tsx package.json package-lock.json
git commit -m "feat(dashboard): toggle bot WhatsApp em /configuracoes"
```

---

## Notas de Teste Manual

Após executar os dois tasks, verificar:

1. Acesse `/configuracoes` — o card "Bot WhatsApp" aparece no topo, toggle ON por padrão (chave ainda não existe no banco)
2. Clique o toggle → OFF → mensagem "Bot desativado." aparece
3. Envie uma mensagem via WhatsApp de teste → logs do worker devem mostrar `skipped_reason=bot_desativado` e a mensagem deve estar salva no banco
4. Reative o toggle → ON → bot volta a responder
