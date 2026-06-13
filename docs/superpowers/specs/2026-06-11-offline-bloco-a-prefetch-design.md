# Offline Bloco A — Prefetch + indicador (Estoque + Clientes) — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile`

## Objetivo
Fazer Estoque e Clientes funcionarem offline de forma confiável pro técnico em campo, atacando o buraco principal: **cache frio**. Hoje o cache-first só serve offline se a tela foi aberta online antes. Solução: **prefetch proativo** (login + reconexão) + **indicador de offline** por tela.

Decisões aprovadas:
- **Escopo leve:** prefetch só da **lista de clientes** + **saldo de estoque** (2 chamadas). Detalhe/materiais ficam fora (detalhe segue cacheando sob demanda como hoje).
- **Quando:** ao logar + quando a conectividade volta (auto). Pull-to-refresh manual segue existindo.
- **Indicador:** chip por tela ("Offline · dados de há X").
- **Sem tabela Drift nova** (reusa `EstoqueLocal` + `ClienteCadastroLocal` que já têm `syncedAt`) — não precisa de `build_runner`.

## Componentes

### 1. `PrefetchService` (`lib/core/sync/prefetch_service.dart`)
Unidade isolada que aquece o cache. Recebe `Dio` + `AppDatabase` (como o `SyncService`).
- `Future<void> prefetchAll()`:
  - `userId = await readUserId()`; se null/vazio → retorna (não logado).
  - GET `/api/v1/tecnico/me/estoque/saldo` → decode `linhas` → `EstoqueLocalRepo(db).replaceAll(userId, rows)`.
  - GET `/api/v1/clientes-campo` (sem filtro) → decode `items` → `ClienteCadastroLocalRepo(db).replaceAll(userId, rows)`.
  - **Best-effort:** cada GET num try/catch próprio (um falhar não derruba o outro); erros logados via `developer.log`, sem throw (é warm-up).
  - Não-reentrante (flag `_running`).
- `start()`: dispara `prefetchAll()` inicial + assina `Connectivity().onConnectivityChanged`; quando online, chama `prefetchAll()`. Idempotente. `stop()` cancela.
- Provider `prefetchServiceProvider` (Provider<PrefetchService>, `ref.onDispose(svc.stop)`).

**Gatilhos:**
- `main.dart` bootstrap: depois de `syncService.start()`, se `hasToken`, chamar `prefetchService.start()`.
- `login_screen._entrar`: após login OK (antes/depois do `context.go('/os')`), `unawaited(ref.read(prefetchServiceProvider).prefetchAll())`.

### 2. Conectividade + idade do cache
- `connectivityStatusProvider` (`lib/core/sync/connectivity_status.dart`): `StreamProvider<bool>` — `true` = online. Emite o estado inicial (`checkConnectivity`) e atualizações (`onConnectivityChanged`); online = qualquer resultado `!= none`.
- Repos ganham `Future<DateTime?> lastSyncedAt({required String userId})`:
  - `EstoqueLocalRepo`: `MAX(syncedAt)` de `estoqueLocal` do user.
  - `ClienteCadastroLocalRepo`: `MAX(syncedAt)` de `clienteCadastroLocal` do user.
- Providers de idade: `estoqueLastSyncedAtProvider` e `clientesLastSyncedAtProvider` (FutureProvider) — leem `lastSyncedAt(userId)`.

### 3. `OfflineCacheChip` (`lib/core/ui/offline_cache_chip.dart`)
Widget reutilizável: `OfflineCacheChip({DateTime? syncedAt})`. Mostra pílula discreta com ícone `cloud_off` + texto:
- `syncedAt != null` → "Offline · dados de há {idade}" (helper: "agora" / "há N min" / "há N h" / "há N dias").
- `syncedAt == null` → "Offline".
Tom: warning (âmbar) suave, sobre `surfaceContainerHigh`.

### 4. Telas
- **Estoque** (`estoque_screen.dart`) e **Clientes lista** (`clientes_list_screen.dart`): logo após o `IosGlassHeader`, um sliver condicional:
  `if (online == false) SliverToBoxAdapter(child: Padding(... OfflineCacheChip(syncedAt: <lastSyncedAt do feature>)))`.
  `online` vem de `connectivityStatusProvider` (`.value ?? true`); `syncedAt` do provider de idade.

## Não muda
- Providers cache-first existentes (`estoqueSaldoProvider`/`clientesListProvider`/`clienteDetailProvider`) — o prefetch só popula o cache que eles já consomem no fallback.
- Detalhe/materiais (sob demanda como hoje). Outbox de OS.

## Critérios de sucesso
1. Logar online → ir pro campo sem abrir Estoque/Clientes → offline, as duas telas mostram dados (cache quente).
2. Rede volta → cache re-sincroniza sozinho.
3. Offline, Estoque e Clientes mostram o chip com a idade do cache.
4. Online segue idêntico (sem chip); nenhum provider existente mudou de tipo.
5. `flutter analyze` limpo (deploy).
6. Visual on-device: chip aparece offline, some online.

## Riscos
- Duas assinaturas de conectividade (`SyncService` + `PrefetchService`) — ok, `connectivity_plus` suporta múltiplos listeners.
- Prefetch no login dispara 2 GETs — fire-and-forget, não bloqueia a navegação.
- `connectivityStatusProvider` "online" não garante internet real (só interface de rede) — o fallback dos providers cache-first continua sendo a verdade; o chip é dica, não bloqueio.
