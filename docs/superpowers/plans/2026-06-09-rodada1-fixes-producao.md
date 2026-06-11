# Rodada 1 — Fixes de Produção (bot + dashboard) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar 5 falhas de produção: SGP fora do ar tratado como "cliente não existe"; turnos LLM concorrentes sem lock (OS duplicada); bot respondendo por cima do atendente; SSE do chat do dashboard 100% quebrado (401); mutações do chat falhando sem feedback.

**Architecture:** Backend: nova exceção `SgpUnavailableError` propagada provider → router → tool (o stale-fallback do cache já existe e passa a funcionar); lock Redis `SET nx` por conversa no `llm_turn` + guards de status/última mensagem. Dashboard: SSE autenticado via ticket JWT de 60s (EventSource não envia header), com fallback de polling, + toasts de erro nas mutações.

**Tech Stack:** FastAPI, Celery, Redis, SQLAlchemy async, httpx/respx, pytest; Next.js + TanStack Query + sonner.

**⚠️ Regras deste repo (sobrepõem o fluxo padrão da skill):**
1. **NÃO rodar pytest/alembic/docker localmente** — não existe stack local. Verificação = CI no push (CI vermelho bloqueia deploy).
2. **NÃO pushar sem OK do Robert.** Commits locais por task; push em 2 levas (backend → frontend) com OK explícito.
3. Push na main = deploy automático (GHCR + Watchtower 30s). **Gotcha:** Watchtower NÃO atualiza os frontends — dashboard precisa de pull manual na VPS após a leva 2.
4. **Evitar pushar a leva backend perto das 9h** — restart do worker durante a régua de cobrança é a brecha #2 da auditoria (reenvio em massa), que ainda não foi corrigida.

---

## Estrutura de arquivos

| Arquivo | Mudança |
|---|---|
| `apps/api/src/ondeline_api/adapters/sgp/base.py` | + `SgpUnavailableError` |
| `apps/api/src/ondeline_api/adapters/sgp/ondeline.py` | provider levanta erro técnico em vez de `None` |
| `apps/api/src/ondeline_api/adapters/sgp/router.py` | propaga indisponibilidade quando ninguém achou |
| `apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py` | trata indisponível com instrução explícita pro LLM |
| `apps/api/src/ondeline_api/workers/llm_turn.py` | lock por conversa + guards status/última msg + requeue |
| `apps/api/src/ondeline_api/auth/jwt.py` | + `encode_sse_ticket`/`decode_sse_ticket` |
| `apps/api/src/ondeline_api/api/v1/conversas_stream.py` | + endpoint de ticket; stream autentica via ticket |
| `apps/dashboard/lib/api/queries.ts` | `useConversa` com polling opcional; onError+toast nas mutações |
| `apps/dashboard/components/conversa-chat.tsx` | SSE via ticket + reconexão + dedup + try/catch |
| `apps/dashboard/components/conversa-list.tsx` | try/catch em encerrar/excluir |
| Testes | `test_sgp_ondeline.py`, `test_sgp_cache.py`, `test_tool_buscar_cliente_sgp.py`, novo `test_llm_turn_guards.py`, `test_jwt.py` |

---

### Task 1: `SgpUnavailableError` — provider distingue "não encontrado" de erro técnico

**Files:**
- Modify: `apps/api/src/ondeline_api/adapters/sgp/base.py`
- Modify: `apps/api/src/ondeline_api/adapters/sgp/ondeline.py:152-171`
- Test: `apps/api/tests/test_sgp_ondeline.py`

- [ ] **Step 1: Adicionar a exceção em `base.py`** (após os imports, antes de `EnderecoSgp`)

```python
class SgpUnavailableError(RuntimeError):
    """Falha tecnica ao consultar o SGP (rede / HTTP != 200 / JSON invalido).

    Distinto de "cliente nao encontrado" (retorno None). Quem cacheia NAO
    deve gravar cache negativo quando isto e levantado; quem responde ao
    cliente NAO deve dizer "cadastro nao encontrado".
    """
```

- [ ] **Step 2: Atualizar os testes existentes que esperavam `None` em erro** (em `test_sgp_ondeline.py`, os dois testes abaixo trocam de assert — renomear junto)

```python
from ondeline_api.adapters.sgp.base import SgpUnavailableError


async def test_buscar_http_error_levanta_unavailable() -> None:
    async with respx.mock(assert_all_called=True) as router:
        router.post(f"{BASE}/api/ura/clientes/").respond(500, json={"err": "x"})
        p = SgpOndelineProvider(base_url=BASE, token="t")
        with pytest.raises(SgpUnavailableError):
            await p.buscar_por_cpf("11122233344")
        await p.aclose()


async def test_buscar_network_error_levanta_unavailable() -> None:
    import httpx as _httpx

    async with respx.mock() as router:
        router.post(f"{BASE}/api/ura/clientes/").mock(
            side_effect=_httpx.ConnectError("boom")
        )
        p = SgpOndelineProvider(base_url=BASE, token="t")
        with pytest.raises(SgpUnavailableError):
            await p.buscar_por_cpf("11122233344")
        await p.aclose()
```

Os testes `test_buscar_nao_encontrado_retorna_none` (200 + lista vazia → `None`) e `test_cpf_vazio_retorna_none` ficam como estão — esse é o comportamento que continua correto.

- [ ] **Step 3: Modificar o provider** — em `ondeline.py`, trocar o trecho das linhas 156–171 por:

```python
        try:
            r = await self._client.post(
                f"{self._base}/api/ura/clientes/",
                data={"token": self._token, "app": self._app, "cpfcnpj": clean},
            )
        except httpx.HTTPError as e:
            log.warning("sgp.ondeline.network_error", error=str(e))
            raise SgpUnavailableError(f"network error: {e}") from e
        if r.status_code != 200:
            log.warning("sgp.ondeline.http_error", status=r.status_code)
            raise SgpUnavailableError(f"http {r.status_code}")
        try:
            data = r.json()
        except Exception as e:
            log.warning("sgp.ondeline.json_decode_error")
            raise SgpUnavailableError("invalid json body") from e
```

E adicionar o import no topo: `from ondeline_api.adapters.sgp.base import SgpUnavailableError` (junto dos demais imports de `base`). LinkNetAM herda de `SgpOndelineProvider` (`linknetam.py:8`), então o fix cobre os dois providers.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/sgp/base.py apps/api/src/ondeline_api/adapters/sgp/ondeline.py apps/api/tests/test_sgp_ondeline.py
git commit -m "fix(sgp): provider distingue 'nao encontrado' de falha tecnica (SgpUnavailableError)"
```

---

### Task 2: Router propaga indisponibilidade (e o stale-fallback do cache passa a funcionar)

**Files:**
- Modify: `apps/api/src/ondeline_api/adapters/sgp/router.py:29-39`
- Test: `apps/api/tests/test_sgp_cache.py` (+ qualquer teste de router: rodar `grep -rl "SgpRouter" apps/api/tests/` e ajustar os que esperavam `None` em erro)

- [ ] **Step 1: Escrever testes novos em `test_sgp_cache.py`** (seguir o padrão de fakes já usado no arquivo — ler o arquivo antes; a semântica a testar):

```python
async def test_sgp_down_serve_stale_do_db(...) -> None:
    # router (fake) levanta SgpUnavailableError; existe linha STALE no DB
    # → get_cliente retorna o stale, e NAO grava sgp:not_found no redis
    ...

async def test_sgp_down_sem_stale_propaga_erro(...) -> None:
    # router levanta SgpUnavailableError; DB vazio
    # → get_cliente re-levanta SgpUnavailableError (nao retorna None!)
    ...
```

Implementar os dois com os fakes/fixtures do próprio `test_sgp_cache.py` (o arquivo já tem fake de redis e de router — reusar). O assert crítico do primeiro: `await redis.get(f"sgp:not_found:{cpf_hash}") is None`.

- [ ] **Step 2: Modificar o router** — substituir `buscar_por_cpf` em `router.py`:

```python
    async def buscar_por_cpf(self, cpf: str) -> ClienteSgp | None:
        clean = _clean_cpf(cpf)
        unavailable = False
        for prov in (self._primary, self._secondary):
            try:
                cli = await prov.buscar_por_cpf(clean)
            except Exception as e:
                log.warning(
                    "sgp.router.provider_error",
                    provider=prov.name.value,
                    error=str(e),
                )
                unavailable = True
                continue
            if cli is not None:
                return cli
        if unavailable:
            # Pelo menos um provider falhou tecnicamente e ninguem achou o
            # cliente — "nao encontrado" nao e confiavel. O caller (cache)
            # serve stale ou propaga; nunca cacheia negativo.
            raise SgpUnavailableError("nenhum provider SGP respondeu com sucesso")
        return None
```

Import no topo: `from ondeline_api.adapters.sgp.base import ClienteSgp, SgpProvider, SgpUnavailableError`.

**Nenhuma mudança em `sgp_cache.py`:** o `except Exception` em `get_cliente` (linha 128) já serve stale do DB e re-levanta sem stale; `_write(cpf_hash, None)` (cache negativo) agora só roda em not-found real. Era código morto que passa a viver.

**Nenhuma mudança na régua:** `cobranca_regua.py:224` já tem `except Exception` que loga e pula o cliente — com SGP fora, a régua pula em vez de tratar como "sem débito". Confirmar lendo o bloco antes de commitar.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/adapters/sgp/router.py apps/api/tests/test_sgp_cache.py
git commit -m "fix(sgp): router propaga indisponibilidade; cache nao envenena negativo com SGP fora"
```

---

### Task 3: Tool `buscar_cliente_sgp` orienta o LLM quando o SGP está fora

**Files:**
- Modify: `apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py:110-113`
- Test: `apps/api/tests/test_tool_buscar_cliente_sgp.py`

- [ ] **Step 1: Teste novo** (seguir o padrão de `ToolContext` fake já usado no arquivo):

```python
async def test_sgp_indisponivel_retorna_instrucao(...) -> None:
    # ctx.sgp_cache.get_cliente levanta SgpUnavailableError
    result = await buscar_cliente_sgp(ctx, cpf_cnpj="11122233344")
    assert result["erro"] == "sgp_indisponivel"
    assert "encontrado" not in result  # NAO pode parecer "nao encontrado"
```

- [ ] **Step 2: Implementação** — no início da função (linha 111):

```python
    try:
        cli_sgp = await ctx.sgp_cache.get_cliente(cpf_cnpj)
    except SgpUnavailableError:
        return {
            "erro": "sgp_indisponivel",
            "instrucao": (
                "O sistema de consulta de cadastro esta temporariamente "
                "instavel. Avise o cliente e peca para tentar de novo em "
                "alguns minutos. NAO diga que o CPF/cadastro nao foi "
                "encontrado."
            ),
        }
    if cli_sgp is None:
        return {"encontrado": False}
```

Import: `from ondeline_api.adapters.sgp.base import SgpUnavailableError`. As demais tools que usam SGP (ex.: `enviar_boleto`) ficam cobertas pelo catch genérico do registry (`tools/registry.py:67-69`), que devolve `{"error": ...}` ao LLM — aceitável; não mexer agora (YAGNI).

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/tools/buscar_cliente_sgp.py apps/api/tests/test_tool_buscar_cliente_sgp.py
git commit -m "fix(bot): SGP indisponivel nao vira 'cadastro nao encontrado' na tool"
```

---

### Task 4: `llm_turn` — lock por conversa + recheck de status + skip se já respondida

**Files:**
- Modify: `apps/api/src/ondeline_api/workers/llm_turn.py`
- Test: `apps/api/tests/test_llm_turn_guards.py` (novo)

- [ ] **Step 1: Teste do guard puro** (arquivo novo):

```python
"""Guards do llm_turn: status da conversa + ultima mensagem."""
from __future__ import annotations

from ondeline_api.db.models.business import ConversaStatus, MensagemRole
from ondeline_api.workers.llm_turn import _skip_reason


def test_roda_quando_bot_e_ultima_msg_cliente() -> None:
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.CLIENTE) is None


def test_skip_quando_humano_assumiu() -> None:
    assert _skip_reason(ConversaStatus.HUMANO, MensagemRole.CLIENTE) == "status_humano"


def test_skip_quando_aguardando_atendente() -> None:
    assert _skip_reason(ConversaStatus.AGUARDANDO, MensagemRole.CLIENTE) == "status_aguardando"


def test_skip_quando_encerrada() -> None:
    assert _skip_reason(ConversaStatus.ENCERRADA, MensagemRole.CLIENTE) == "status_encerrada"


def test_skip_quando_bot_ja_respondeu() -> None:
    # turno requeued chegou depois do turno anterior ja ter coberto a msg
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.BOT) == "ja_respondida"
    assert _skip_reason(ConversaStatus.BOT, MensagemRole.ATENDENTE) == "ja_respondida"


def test_roda_em_conversa_sem_mensagens() -> None:
    # defensivo: sem historico nao bloqueia (caso teorico)
    assert _skip_reason(ConversaStatus.BOT, None) is None
```

- [ ] **Step 2: Implementar em `llm_turn.py`.** Adicionar constantes, o guard e reescrever `_run`/task:

Imports adicionais no topo:

```python
from ondeline_api.db.models.business import Cliente, Conversa, ConversaStatus, MensagemRole
from ondeline_api.repositories.mensagem import MensagemRepo
```

Constantes e guard (antes de `_run`):

```python
LOCK_TTL_SECONDS = 90
MAX_REQUEUES = 15
REQUEUE_DELAY_SECONDS = 8


def _skip_reason(status: ConversaStatus, last_role: MensagemRole | None) -> str | None:
    """None = turno deve rodar; senao, motivo do skip.

    - Conversa fora de BOT: atendente assumiu / escalou / encerrou entre o
      enfileiramento e a execucao — bot NAO pode responder por cima.
    - Ultima mensagem nao e do cliente: um turno anterior (concorrente,
    serializado pelo lock) ja respondeu — evita resposta duplicada.
    """
    if status is not ConversaStatus.BOT:
        return f"status_{status.value}"
    if last_role is not None and last_role is not MensagemRole.CLIENTE:
        return "ja_respondida"
    return None
```

`_run` ganha o lock no início e os guards após carregar a conversa (corpo atual preservado; mudanças marcadas):

```python
async def _run(conversa_id: UUID) -> dict[str, Any]:
    s = get_settings()
    redis = await get_redis()

    # Lock por conversa: serializa turnos concorrentes (3 msgs seguidas do
    # cliente = 3 tasks). Quem nao pega o lock e re-enfileirado pela task.
    lock_key = f"llm:lock:{conversa_id}"
    got_lock = bool(await redis.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS))
    if not got_lock:
        log.info("llm_turn.locked", conversa_id=str(conversa_id))
        return {"conversa_id": str(conversa_id), "skipped": "locked"}

    try:
        llm_url, llm_key, llm_model = s.effective_llm()
        provider = HermesProvider(...)        # ← corpo existente inalterado
        budget = TokensBudget(...)
        router: SgpRouter | None = None
        evolution: WhatsAppAdapter | None = None
        try:
            async with task_session() as session:
                evolution = await adapter_for_conversa(session, conversa_id, s)
                ...                            # setup existente inalterado
                conversa = (
                    await session.execute(select(Conversa).where(Conversa.id == conversa_id))
                ).scalar_one()

                # Guards: status pode ter mudado e/ou outro turno ja respondeu.
                history = await MensagemRepo(session).list_history(conversa_id, limit=1)
                last_role = history[-1].role if history else None
                reason = _skip_reason(conversa.status, last_role)
                if reason is not None:
                    log.info("llm_turn.skip", conversa_id=str(conversa_id), reason=reason)
                    return {"conversa_id": str(conversa_id), "skipped": reason}

                ...                            # resto do corpo existente (cliente, cache, ctx, run_turn)
        finally:
            await provider.aclose()
            if router is not None:
                await router.aclose()
            if evolution is not None:
                await evolution.aclose()
    finally:
        # Libera o lock SEMPRE (apos commit da task_session). TTL de 90s e o
        # backstop se o worker morrer aqui.
        try:
            await redis.delete(lock_key)
        except Exception:
            log.warning("llm_turn.lock_release_failed", conversa_id=str(conversa_id))
```

Atenção do executor: é uma re-indentação do corpo existente dentro do novo `try/finally` externo — não alterar a lógica interna existente (setup de providers, `run_turn`, log final e dict de retorno seguem idênticos).

Task com requeue (substitui a atual):

```python
@celery_app.task(
    name="ondeline_api.workers.llm_turn.llm_turn_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def llm_turn_task(self: Any, *, conversa_id: str, requeued: int = 0) -> dict[str, Any]:
    cid = UUID(conversa_id)
    try:
        result = cast(dict[str, Any], run_task(lambda: _run(cid)))
    except Exception as e:
        raise self.retry(exc=e) from e
    if result.get("skipped") == "locked" and requeued < MAX_REQUEUES:
        # Outro turno esta rodando: tenta de novo em alguns segundos. O guard
        # "ja_respondida" garante que o requeue nao gera resposta duplicada.
        llm_turn_task.apply_async(
            kwargs={"conversa_id": conversa_id, "requeued": requeued + 1},
            countdown=REQUEUE_DELAY_SECONDS,
        )
    return result
```

Callers existentes usam `.delay(conversa_id=...)` (`runtime.py:110,224`, `asr_jobs.py:73`) — o kwarg novo tem default, sem mudança neles.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/ondeline_api/workers/llm_turn.py apps/api/tests/test_llm_turn_guards.py
git commit -m "fix(bot): lock por conversa no llm_turn + nao responde por cima do atendente"
```

---

### Task 5: SSE com ticket de 60s (backend)

**Files:**
- Modify: `apps/api/src/ondeline_api/auth/jwt.py` (após `encode_cliente_access_token`)
- Modify: `apps/api/src/ondeline_api/api/v1/conversas_stream.py`
- Test: `apps/api/tests/test_jwt.py`

Por que ticket: `EventSource` não envia header `Authorization` (causa do 401 atual, `auth/deps.py:14-21`). Token de 15 min em query string vazaria pra access log; um ticket de 60s, `type=sse`, amarrado à conversa, não serve pra mais nada e expira antes de log virar risco.

- [ ] **Step 1: Testes em `test_jwt.py`** (seguir imports/estilo do arquivo):

```python
def test_sse_ticket_roundtrip() -> None:
    uid, cid = uuid4(), uuid4()
    t = jwt_mod.encode_sse_ticket(uid, "atendente", cid)
    p = jwt_mod.decode_sse_ticket(t)
    assert p["sub"] == str(uid)
    assert p["conversa_id"] == str(cid)
    assert p["role"] == "atendente"


def test_sse_ticket_nao_e_aceito_como_access_token() -> None:
    t = jwt_mod.encode_sse_ticket(uuid4(), "admin", uuid4())
    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_access_token(t)


def test_access_token_nao_e_aceito_como_ticket() -> None:
    t = jwt_mod.encode_access_token(uuid4(), "admin")
    with pytest.raises(jwt_mod.InvalidTokenType):
        jwt_mod.decode_sse_ticket(t)
```

- [ ] **Step 2: `jwt.py`** — adicionar:

```python
SSE_TICKET_TTL_SECONDS = 60


def encode_sse_ticket(user_id: UUID, role: str, conversa_id: UUID) -> str:
    """Ticket curto pro EventSource (que nao envia Authorization header).

    type=sse: nao e aceito como access token (e vice-versa) — _decode valida.
    Amarrado a UMA conversa; 60s de vida (so pra abrir a conexao).
    """
    iat = _now()
    exp = iat + timedelta(seconds=SSE_TICKET_TTL_SECONDS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "conversa_id": str(conversa_id),
        "kind": "staff",
        "type": "sse",
        "jti": str(uuid4()),
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGO)


def decode_sse_ticket(token: str) -> dict[str, Any]:
    return _decode(token, "sse")
```

- [ ] **Step 3: `conversas_stream.py`** — versão nova completa:

```python
"""SSE endpoint for live conversation events.

EventSource nao envia Authorization header. Fluxo: o front faz POST
/stream-ticket (autenticado normal) e abre o GET /stream?ticket=<jwt 60s>.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ondeline_api.auth import jwt as jwt_mod
from ondeline_api.auth.deps import get_current_user
from ondeline_api.auth.rbac import require_role
from ondeline_api.db.models.identity import Role, User
from ondeline_api.deps import get_db
from ondeline_api.repositories.conversa import ConversaRepo
from ondeline_api.services.conversa_events import subscribe
from ondeline_api.workers.runtime import get_redis

router = APIRouter(prefix="/api/v1/conversas", tags=["conversas-stream"])

_ROLES_STREAM = (Role.ATENDENTE.value, Role.ADMIN.value)


@router.post(
    "/{conversa_id}/stream-ticket",
    dependencies=[Depends(require_role(Role.ATENDENTE, Role.ADMIN))],
)
async def stream_ticket(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {"ticket": jwt_mod.encode_sse_ticket(user.id, role, conversa_id)}


@router.get("/{conversa_id}/stream")
async def stream_conversa(
    conversa_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    ticket: Annotated[str, Query()],
) -> EventSourceResponse:
    try:
        payload = jwt_mod.decode_sse_ticket(ticket)
    except jwt_mod.TokenExpired:
        raise HTTPException(status_code=401, detail="ticket expired") from None
    except (jwt_mod.InvalidToken, jwt_mod.InvalidTokenType) as exc:
        raise HTTPException(status_code=401, detail="invalid ticket") from exc
    if payload.get("conversa_id") != str(conversa_id):
        raise HTTPException(status_code=403, detail="ticket nao corresponde a conversa")
    if payload.get("role") not in _ROLES_STREAM:
        raise HTTPException(status_code=403, detail="role nao autorizado")

    repo = ConversaRepo(session)
    c = await repo.get_by_id(conversa_id)
    if c is None:
        raise HTTPException(status_code=404, detail="conversa not found")

    async def _gen() -> AsyncIterator[dict[str, str]]:
        redis = await get_redis()
        async for event in subscribe(redis, conversa_id):
            yield {"event": event.get("type", "msg"), "data": json.dumps(event)}

    return EventSourceResponse(_gen())
```

Conferir em `auth/jwt.py` se `InvalidTokenType` herda de `InvalidToken`; se herdar, o catch duplo é redundante mas inofensivo. Conferir o nome real do atributo de role em `db/models/identity.py` (`User.role`).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/ondeline_api/auth/jwt.py apps/api/src/ondeline_api/api/v1/conversas_stream.py apps/api/tests/test_jwt.py
git commit -m "fix(dashboard): SSE autentica via ticket de 60s (EventSource nao envia bearer)"
```

> **CHECKPOINT — leva backend completa.** Pedir OK do Robert pra push (fora do horário da régua). CI valida; Watchtower deploya API+worker+beat. Verificar em prod: `docker logs blabla-api` sem erro de import; abrir uma conversa de teste e confirmar `llm_turn.skip`/`llm_turn.locked` nos logs do worker quando mandar 2 msgs rápidas.

---

### Task 6: SSE no front — ticket, reconexão, fallback de polling, dedup

**Files:**
- Modify: `apps/dashboard/lib/api/queries.ts:439-445` (`useConversa`)
- Modify: `apps/dashboard/components/conversa-chat.tsx:95-129`

- [ ] **Step 1: `useConversa` com polling opcional** (queries.ts):

```ts
export function useConversa(
  id: string,
  opts?: { refetchInterval?: number | false },
) {
  return useQuery<ConversaDetail>({
    queryKey: ['conversa', id],
    queryFn: () => apiFetch(`/api/v1/conversas/${id}`),
    enabled: Boolean(id),
    refetchInterval: opts?.refetchInterval ?? false,
  })
}
```

- [ ] **Step 2: `conversa-chat.tsx`** — substituir o useEffect do SSE (linhas 95-124) e o `allMsgs` (linha 126):

Novo estado + import (`import { apiFetch } from '@/lib/api/client'` — conferir o path usado pelo próprio queries.ts):

```tsx
const [sseDown, setSseDown] = useState(false)
```

Na chamada existente do hook: `useConversa(conversaId, { refetchInterval: sseDown ? 10_000 : false })` — se o SSE cair, o chat degrada pra polling de 10s em vez de ficar cego.

```tsx
// SSE real-time (ticket de 60s: EventSource nao envia Authorization)
useEffect(() => {
  if (!conversaId) return
  let es: EventSource | null = null
  let cancelled = false
  let retryTimer: ReturnType<typeof setTimeout> | null = null

  async function connect(attempt: number) {
    try {
      const { ticket } = await apiFetch<{ ticket: string }>(
        `/api/v1/conversas/${conversaId}/stream-ticket`,
        { method: 'POST' },
      )
      if (cancelled) return
      es = new EventSource(
        `/api/v1/conversas/${conversaId}/stream?ticket=${encodeURIComponent(ticket)}`,
      )
      es.onopen = () => setSseDown(false)
      es.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data as string) as SseEvent
          if (payload.type !== 'msg' || !payload.role) return
          if (!payload.text && !payload.media_url) return
          setLiveMsgs((prev) => [
            ...prev,
            {
              id: payload.id ?? `live-${Date.now()}`,
              conversa_id: conversaId,
              role: payload.role as MensagemOut['role'],
              content: payload.text ?? null,
              media_type: payload.media_type ?? null,
              media_url: payload.media_url ?? null,
              created_at: payload.ts ?? new Date().toISOString(),
            },
          ])
        } catch { /* ignore */ }
      }
      es.onerror = () => {
        es?.close()
        if (cancelled) return
        setSseDown(true)
        retryTimer = setTimeout(
          () => connect(attempt + 1),
          Math.min(30_000, 2_000 * 2 ** attempt),
        )
      }
    } catch {
      if (cancelled) return
      setSseDown(true)
      retryTimer = setTimeout(
        () => connect(attempt + 1),
        Math.min(30_000, 2_000 * 2 ** attempt),
      )
    }
  }

  void connect(0)
  return () => {
    cancelled = true
    if (retryTimer) clearTimeout(retryTimer)
    es?.close()
  }
}, [conversaId])
```

Dedup (substitui a linha 126 — refetch + SSE entregavam a mesma mensagem duplicada):

```tsx
const baseMsgs = data?.mensagens ?? []
const baseIds = new Set(baseMsgs.map((m) => m.id))
const allMsgs = [...baseMsgs, ...liveMsgs.filter((m) => !baseIds.has(m.id))]
```

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/lib/api/queries.ts apps/dashboard/components/conversa-chat.tsx
git commit -m "fix(dashboard): chat tempo-real funcional — SSE via ticket + fallback polling + dedup"
```

---

### Task 7: Feedback de erro nas mutações do chat

**Files:**
- Modify: `apps/dashboard/lib/api/queries.ts:447-481` (useResponder/useAtender/useEncerrar; + `useDeleteConversa`)
- Modify: `apps/dashboard/components/conversa-chat.tsx:179-185` (handleSend)
- Modify: `apps/dashboard/components/conversa-list.tsx:25-33`

- [ ] **Step 1: `onError` + toast nos hooks** (centraliza: cobre conversa-chat E conversa-list). Em queries.ts, `import { toast } from 'sonner'` e em cada hook:

```ts
export function useResponder(conversaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) =>
      apiFetch(`/api/v1/conversas/${conversaId}/responder`, {
        method: 'POST',
        body: JSON.stringify({ text }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conversa', conversaId] }),
    onError: (err) =>
      toast.error(
        err instanceof Error ? `Falha ao enviar: ${err.message}` : 'Falha ao enviar mensagem',
      ),
  })
}
```

Mesmo padrão em `useAtender` (`'Falha ao assumir conversa'`), `useEncerrar` (`'Falha ao encerrar'`) e `useDeleteConversa` (`'Falha ao excluir'`).

- [ ] **Step 2: handlers não explodem como unhandled rejection** (o texto digitado é preservado pro retry):

`conversa-chat.tsx`:

```tsx
async function handleSend() {
  const trimmed = text.trim()
  if (!trimmed) return
  try {
    await responder.mutateAsync(trimmed)
    setText('')
    void refetch()
  } catch {
    // toast ja emitido no onError do hook; mantem o texto pro retry
  }
}
```

`conversa-list.tsx`:

```tsx
async function handleEncerrar() {
  if (!confirm('Encerrar esta conversa?')) return
  try {
    await encerrar.mutateAsync()
  } catch { /* toast no onError do hook */ }
}

async function handleExcluir() {
  if (!confirm('Excluir esta conversa? O histórico será preservado por 30 dias.')) return
  try {
    await excluir.mutateAsync()
  } catch { /* toast no onError do hook */ }
}
```

Os botões `atender.mutate()` / `encerrar.mutate()` em conversa-chat.tsx:546/561 já ficam cobertos pelo `onError` dos hooks (`.mutate` não rejeita promise).

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/lib/api/queries.ts apps/dashboard/components/conversa-chat.tsx apps/dashboard/components/conversa-list.tsx
git commit -m "fix(dashboard): toast de erro em responder/atender/encerrar/excluir (fim da falha silenciosa)"
```

> **CHECKPOINT — leva frontend completa.** Pedir OK pra push. Lembrar: Watchtower não atualiza o dashboard — fazer pull/recreate manual do `blabla-dashboard` na VPS. Verificação em prod: abrir conversa no dashboard, mandar mensagem pelo WhatsApp e ver chegar SEM trocar de aba; derrubar a rede e ver o toast de erro ao enviar.

---

## Verificação final (depois dos 2 deploys)

1. WhatsApp → mensagem nova aparece no chat aberto em <2s (SSE) — e em ~10s com SSE derrubado (fallback).
2. Mandar 3 mensagens seguidas pro bot → logs do worker mostram `llm_turn.locked` + requeue + `ja_respondida`; UMA resposta só.
3. Atendente clica "Assumir" enquanto bot processa → log `llm_turn.skip reason=status_humano`, bot não responde.
4. (Janela controlada) bloquear saída pro SGP na VPS por 1 min → bot responde "sistema instável", NÃO "cadastro não encontrado"; redis sem `sgp:not_found` novo.
