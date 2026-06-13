# Offline Bloco A (Prefetch + indicador) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Estoque e Clientes confiáveis offline via prefetch proativo (login/reconexão) + chip de offline por tela.

**Architecture:** `PrefetchService` aquece o cache (reusa `EstoqueLocalRepo`/`ClienteCadastroLocalRepo`). Indicador: `connectivityStatusProvider` + `lastSyncedAt` nos repos + `OfflineCacheChip`. Sem tabela Drift nova; providers cache-first existentes inalterados.

**Tech Stack:** Flutter, Riverpod, Dio, Drift, connectivity_plus (todos já no projeto).

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`. Sem teste automatizado (serviços network/UI sem harness; validar via analyze + on-device).

---

## File Structure
- **Create:** `lib/core/sync/prefetch_service.dart`, `lib/core/sync/connectivity_status.dart`, `lib/core/ui/offline_cache_chip.dart`.
- **Modify:** `lib/core/db/estoque_repo.dart`, `lib/core/db/cliente_cadastro_repo.dart` (lastSyncedAt); `lib/features/estoque/estoque_data.dart`, `lib/features/clientes/cliente_data.dart` (lastSync providers); `lib/main.dart`, `lib/features/auth/login_screen.dart` (gatilhos); `lib/features/estoque/estoque_screen.dart`, `lib/features/clientes/clientes_list_screen.dart` (chip).

---

### Task 1: `PrefetchService`

**Files:** Create `lib/core/sync/prefetch_service.dart`

- [ ] **Step 1: Criar o serviço**
```dart
import 'dart:async';
import 'dart:developer' as developer;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../auth/auth_storage.dart';
import '../db/cliente_cadastro_repo.dart';
import '../db/database.dart';
import '../db/estoque_repo.dart';

/// Aquece o cache offline (estoque + lista de clientes) proativamente, pra o
/// fallback cache-first ter dados mesmo se o técnico não abriu as telas online.
class PrefetchService {
  final Dio _dio;
  final AppDatabase _db;
  StreamSubscription<List<ConnectivityResult>>? _connSub;
  bool _running = false;

  PrefetchService(this._dio, this._db);

  /// Prefetch inicial + re-prefetch quando a rede volta. Idempotente.
  Future<void> start() async {
    unawaited(prefetchAll());
    _connSub ??= Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) unawaited(prefetchAll());
    });
  }

  Future<void> stop() async {
    await _connSub?.cancel();
    _connSub = null;
  }

  /// Best-effort: aquece o cache. Não lança (warm-up). Não-reentrante.
  Future<void> prefetchAll() async {
    if (_running) return;
    _running = true;
    try {
      final userId = await readUserId();
      if (userId == null || userId.isEmpty) return;
      await _prefetchEstoque(userId);
      await _prefetchClientes(userId);
    } finally {
      _running = false;
    }
  }

  Future<void> _prefetchEstoque(String userId) async {
    try {
      final r = await _dio.get('/api/v1/tecnico/me/estoque/saldo');
      final raw = r.data as Map<String, dynamic>;
      final rows = (raw['linhas'] as List? ?? const [])
          .whereType<Map>()
          .map((m) => m.cast<String, dynamic>())
          .toList();
      await EstoqueLocalRepo(_db).replaceAll(userId: userId, rows: rows);
    } catch (e) {
      developer.log('prefetch estoque falhou',
          name: 'PrefetchService', error: e);
    }
  }

  Future<void> _prefetchClientes(String userId) async {
    try {
      final r = await _dio.get('/api/v1/clientes-campo');
      final raw = r.data as Map<String, dynamic>;
      final rows = (raw['items'] as List? ?? const [])
          .whereType<Map>()
          .map((m) => m.cast<String, dynamic>())
          .toList();
      await ClienteCadastroLocalRepo(_db).replaceAll(userId: userId, rows: rows);
    } catch (e) {
      developer.log('prefetch clientes falhou',
          name: 'PrefetchService', error: e);
    }
  }
}

final prefetchServiceProvider = Provider<PrefetchService>((ref) {
  final svc =
      PrefetchService(ref.watch(apiClientProvider), ref.watch(dbProvider));
  ref.onDispose(svc.stop);
  return svc;
});
```

- [ ] **Step 2: Commit**
```bash
git add lib/core/sync/prefetch_service.dart
git commit --no-verify -m "feat(tecnico-mobile): PrefetchService aquece cache offline (estoque + clientes)"
```

---

### Task 2: Infra do indicador (conectividade + idade + chip)

**Files:** Create `connectivity_status.dart` + `offline_cache_chip.dart`; modify os 2 repos + os 2 data files.

- [ ] **Step 1: `lib/core/sync/connectivity_status.dart`**
```dart
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Online (true) / offline (false) pela interface de rede. Dica de UI —
/// não garante internet real (o fallback cache-first é a verdade).
final connectivityStatusProvider = StreamProvider<bool>((ref) async* {
  bool online(List<ConnectivityResult> r) =>
      r.any((c) => c != ConnectivityResult.none);
  yield online(await Connectivity().checkConnectivity());
  yield* Connectivity().onConnectivityChanged.map(online);
});
```

- [ ] **Step 2: `EstoqueLocalRepo.lastSyncedAt`** — adicionar em `lib/core/db/estoque_repo.dart` (antes de `clear`):
```dart
  Future<DateTime?> lastSyncedAt({required String userId}) async {
    final maxExp = _db.estoqueLocal.syncedAt.max();
    final row = await (_db.selectOnly(_db.estoqueLocal)
          ..addColumns([maxExp])
          ..where(_db.estoqueLocal.userId.equals(userId)))
        .getSingle();
    return row.read(maxExp);
  }
```

- [ ] **Step 3: `ClienteCadastroLocalRepo.lastSyncedAt`** — adicionar em `lib/core/db/cliente_cadastro_repo.dart` (antes de `clear`):
```dart
  Future<DateTime?> lastSyncedAt({required String userId}) async {
    final maxExp = _db.clienteCadastroLocal.syncedAt.max();
    final row = await (_db.selectOnly(_db.clienteCadastroLocal)
          ..addColumns([maxExp])
          ..where(_db.clienteCadastroLocal.userId.equals(userId)))
        .getSingle();
    return row.read(maxExp);
  }
```

- [ ] **Step 4: Provider de idade — estoque** (`lib/features/estoque/estoque_data.dart`, no fim):
```dart
final estoqueLastSyncedAtProvider = FutureProvider<DateTime?>((ref) async {
  final repo = ref.watch(estoqueLocalRepoProvider);
  final userId = await ref.watch(estoqueReadUserIdProvider)();
  if (userId == null || userId.isEmpty) return null;
  return repo.lastSyncedAt(userId: userId);
});
```

- [ ] **Step 5: Provider de idade — clientes** (`lib/features/clientes/cliente_data.dart`, no fim):
```dart
final clientesLastSyncedAtProvider = FutureProvider<DateTime?>((ref) async {
  final repo = ref.watch(clienteCadastroRepoProvider);
  final userId = await ref.watch(clienteReadUserIdProvider)();
  if (userId == null || userId.isEmpty) return null;
  return repo.lastSyncedAt(userId: userId);
});
```

- [ ] **Step 6: `lib/core/ui/offline_cache_chip.dart`**
```dart
import 'package:flutter/material.dart';

/// Pílula discreta exibida quando offline, com a idade do cache servido.
class OfflineCacheChip extends StatelessWidget {
  const OfflineCacheChip({super.key, this.syncedAt});

  final DateTime? syncedAt;

  static const _amber = Color(0xFFB45309);
  static const _amberBase = Color(0xFFF59E0B);

  @override
  Widget build(BuildContext context) {
    final label = syncedAt == null
        ? 'Offline'
        : 'Offline · dados de ${_idade(syncedAt!)}';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _amberBase.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _amberBase.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_rounded, size: 16, color: _amber),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: _amber,
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _idade(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 1) return 'agora';
    if (d.inMinutes < 60) return 'há ${d.inMinutes} min';
    if (d.inHours < 24) return 'há ${d.inHours} h';
    return 'há ${d.inDays} ${d.inDays == 1 ? 'dia' : 'dias'}';
  }
}
```

- [ ] **Step 7: Commit**
```bash
git add lib/core/sync/connectivity_status.dart lib/core/ui/offline_cache_chip.dart lib/core/db/estoque_repo.dart lib/core/db/cliente_cadastro_repo.dart lib/features/estoque/estoque_data.dart lib/features/clientes/cliente_data.dart
git commit --no-verify -m "feat(tecnico-mobile): infra do indicador offline (conectividade + idade + chip)"
```

---

### Task 3: Gatilhos do prefetch + chip nas telas

**Files:** Modify `main.dart`, `login_screen.dart`, `estoque_screen.dart`, `clientes_list_screen.dart`.

- [ ] **Step 1: `main.dart` — start no bootstrap**

Adicionar import:
```dart
import 'dart:async';
```
(e `import 'core/sync/prefetch_service.dart';` junto dos outros `core/sync`). Depois de `await ref.read(syncServiceProvider).start();`, adicionar:
```dart
      unawaited(ref.read(prefetchServiceProvider).start());
```
(`prefetchAll` checa userId internamente — no-op se deslogado; o listener de reconexão fica ativo.)

- [ ] **Step 2: `login_screen.dart` — dispara no login OK**

Adicionar `import '../../core/sync/prefetch_service.dart';`. No `_entrar`, logo após o bloco do FCM (`unawaited(ref.read(fcmServiceProvider).init());`) e antes de `context.go('/os')`:
```dart
      unawaited(ref.read(prefetchServiceProvider).prefetchAll());
```

- [ ] **Step 3: Chip no Estoque** (`estoque_screen.dart`)

Adicionar imports:
```dart
import '../../core/sync/connectivity_status.dart';
import '../../core/ui/offline_cache_chip.dart';
```
No `CustomScrollView`, logo APÓS o `IosGlassHeader(...)` e ANTES do `...async.when<List<Widget>>(`:
```dart
            if (ref.watch(connectivityStatusProvider).value == false)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: OfflineCacheChip(
                    syncedAt: ref.watch(estoqueLastSyncedAtProvider).value,
                  ),
                ),
              ),
```

- [ ] **Step 4: Chip nos Clientes** (`clientes_list_screen.dart`)

Mesmos 2 imports. No `CustomScrollView`, logo APÓS o `IosGlassHeader(...)` e ANTES do `SliverToBoxAdapter` do KPI:
```dart
            if (ref.watch(connectivityStatusProvider).value == false)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: OfflineCacheChip(
                    syncedAt: ref.watch(clientesLastSyncedAtProvider).value,
                  ),
                ),
              ),
```

- [ ] **Step 5: Commit**
```bash
git add lib/main.dart lib/features/auth/login_screen.dart lib/features/estoque/estoque_screen.dart lib/features/clientes/clientes_list_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): dispara prefetch (login/bootstrap) + chip offline nas telas"
```

---

### Task 4: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/core/sync/ lib/core/ui/offline_cache_chip.dart lib/core/db/ lib/features/estoque/ lib/features/clientes/ lib/main.dart lib/features/auth/login_screen.dart` → limpo.
- [ ] **Step 2: Teste on-device:**
  - Logar online → SEM abrir Estoque/Clientes, ativar modo avião → abrir as duas: mostram dados (cache quente) + chip "Offline · dados de há …".
  - Religar a rede → chip some; dados re-sincronizam (puxar pra atualizar confirma).
  - Online: sem chip, comportamento idêntico ao de hoje.

---

## Self-Review

**Spec coverage:**
- `PrefetchService` (estoque+clientes, best-effort, start/reconnect) → Task 1. ✅
- Gatilhos login + bootstrap → Task 3 Steps 1-2. ✅
- `connectivityStatusProvider` + `lastSyncedAt` nos repos + providers de idade → Task 2. ✅
- `OfflineCacheChip` + exibição nas 2 telas → Task 2 Step 6 + Task 3 Steps 3-4. ✅
- Sem tabela nova; providers cache-first/detalhe inalterados. ✅

**Placeholder scan:** sem TBD; código completo.

**Type consistency:** `replaceAll(userId:, rows:)` bate com os repos; `readUserId()` (auth_storage) usado no service; `estoqueLocalRepoProvider`/`estoqueReadUserIdProvider`/`clienteCadastroRepoProvider`/`clienteReadUserIdProvider` já existem; `connectivityStatusProvider.value` é `bool?` (`== false` só quando offline confirmado); `syncedAt.max()` → `Expression<DateTime>` lido via `row.read`.
