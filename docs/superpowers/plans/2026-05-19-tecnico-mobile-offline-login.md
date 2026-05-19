# Técnico Mobile Offline + Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a sincronização offline, adicionar cache real para estoque e perfil, aplicar atualização otimista de OS e evoluir o login com reentrada por Face ID no iOS.

**Architecture:** A entrega expande o schema Drift para incluir novos snapshots locais e metadados de retry, move `estoque` e `perfil` para providers `read-through`, adiciona mutações otimistas no cache de OS e separa autenticação completa de reentrada local protegida por biometria. O roteamento inicial passa a distinguir login completo, reentrada biométrica e sessão inválida por `401`.

**Tech Stack:** Flutter, Riverpod, Drift/SQLite, Dio, go_router, flutter_secure_storage, connectivity_plus, local_auth, flutter_test

---

### Task 1: Preparar dependência e testes do retry da outbox

**Files:**
- Modify: `apps/tecnico-mobile/pubspec.yaml`
- Create: `apps/tecnico-mobile/test/core/sync/sync_service_test.dart`

- [ ] **Step 1: Write the failing tests for retry based on last attempt**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';

void main() {
  test('backoff uses lastAttemptAt when present', () {
    final now = DateTime(2026, 5, 19, 12);
    final createdAt = now.subtract(const Duration(hours: 5));
    final lastAttemptAt = now.subtract(const Duration(seconds: 5));

    final next = computeNextRetryAt(
      attempts: 2,
      createdAt: createdAt,
      lastAttemptAt: lastAttemptAt,
    );

    expect(next, lastAttemptAt.add(const Duration(seconds: 4)));
  });

  test('backoff falls back to createdAt when item never retried', () {
    final createdAt = DateTime(2026, 5, 19, 12);

    final next = computeNextRetryAt(
      attempts: 3,
      createdAt: createdAt,
      lastAttemptAt: null,
    );

    expect(next, createdAt.add(const Duration(seconds: 8)));
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: FAIL because `computeNextRetryAt` does not exist yet

- [ ] **Step 3: Add local_auth dependency placeholder and minimal retry helper**

```yaml
dependencies:
  local_auth: ^2.3.0
```

```dart
DateTime computeNextRetryAt({
  required int attempts,
  required DateTime createdAt,
  required DateTime? lastAttemptAt,
}) {
  final base = lastAttemptAt ?? createdAt;
  final waitSec = (1 << attempts.clamp(0, 8)).clamp(2, 300);
  return base.add(Duration(seconds: waitSec));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/pubspec.yaml apps/tecnico-mobile/test/core/sync/sync_service_test.dart apps/tecnico-mobile/lib/core/sync/sync_service.dart
git commit -m "test: add outbox retry timing coverage"
```

### Task 2: Persistir lastAttemptAt na outbox

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/db/tables.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/database.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/database.g.dart`
- Modify: `apps/tecnico-mobile/lib/core/sync/outbox_repo.dart`
- Test: `apps/tecnico-mobile/test/core/sync/sync_service_test.dart`

- [ ] **Step 1: Write the failing test for markAttempt timestamp persistence**

```dart
test('markAttempt increments attempts and updates lastAttemptAt', () async {
  final db = testDatabase();
  final repo = OutboxRepo(db);
  final id = await repo.enqueue(
    osId: 'os-1',
    kind: OutboxKind.iniciar,
    payload: const {'lat': 1},
  );

  await repo.markAttempt(id, 'timeout');

  final item = (await repo.pending()).single;
  expect(item.attempts, 1);
  expect(item.lastError, 'timeout');
  expect(item.lastAttemptAt, isNotNull);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: FAIL because `lastAttemptAt` is not in schema yet

- [ ] **Step 3: Update schema and repository**

```dart
DateTimeColumn get lastAttemptAt => dateTime().nullable()();
```

```dart
Future<void> markAttempt(int id, String? error) async {
  final row = await (_db.select(_db.outboxItem)..where((o) => o.id.equals(id)))
      .getSingleOrNull();
  if (row == null) return;

  await (_db.update(_db.outboxItem)..where((o) => o.id.equals(id))).write(
    OutboxItemCompanion(
      attempts: Value(row.attempts + 1),
      lastError: Value(error),
      lastAttemptAt: Value(DateTime.now()),
    ),
  );
}
```

- [ ] **Step 4: Regenerate drift code and run test**

Run: `dart run build_runner build --delete-conflicting-outputs`
Expected: codegen updates `database.g.dart`

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/db/tables.dart apps/tecnico-mobile/lib/core/db/database.g.dart apps/tecnico-mobile/lib/core/sync/outbox_repo.dart apps/tecnico-mobile/test/core/sync/sync_service_test.dart
git commit -m "feat: persist outbox retry attempts"
```

### Task 3: Corrigir uso do backoff no sync service

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/sync/sync_service.dart`
- Test: `apps/tecnico-mobile/test/core/sync/sync_service_test.dart`

- [ ] **Step 1: Write the failing test for retry eligibility**

```dart
test('shouldAttempt waits until retry window after last attempt', () {
  final now = DateTime(2026, 5, 19, 12, 0, 10);
  final item = fakeOutboxItem(
    attempts: 2,
    createdAt: DateTime(2026, 5, 19, 11),
    lastAttemptAt: DateTime(2026, 5, 19, 12, 0, 8),
  );

  expect(shouldAttemptAt(item, now), isFalse);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: FAIL because `shouldAttemptAt` does not exist

- [ ] **Step 3: Implement pure helper and switch service to use it**

```dart
bool shouldAttemptAt(OutboxItemData item, DateTime now) {
  if (item.attempts == 0) return true;
  return now.isAfter(
    computeNextRetryAt(
      attempts: item.attempts,
      createdAt: item.createdAt,
      lastAttemptAt: item.lastAttemptAt,
    ),
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/sync/sync_service_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/sync/sync_service.dart apps/tecnico-mobile/test/core/sync/sync_service_test.dart
git commit -m "fix: use last retry timestamp in sync backoff"
```

### Task 4: Adicionar tabelas locais para estoque e perfil

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/db/tables.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/database.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/database.g.dart`
- Create: `apps/tecnico-mobile/lib/core/db/estoque_repo.dart`
- Create: `apps/tecnico-mobile/lib/core/db/perfil_repo.dart`
- Create: `apps/tecnico-mobile/test/core/db/offline_cache_test.dart`

- [ ] **Step 1: Write the failing tests for local cache repositories**

```dart
test('estoque repo round-trips cached rows', () async {
  final db = testDatabase();
  final repo = EstoqueLocalRepo(db);

  await repo.replaceAll([
    {'item_id': '1', 'sku': 'CABO', 'nome': 'Cabo', 'categoria': 'Rede', 'serializado': false, 'saldo': 3}
  ]);

  final rows = await repo.listAll();
  expect(rows.single['sku'], 'CABO');
});

test('perfil repo returns last cached snapshot', () async {
  final db = testDatabase();
  final repo = PerfilLocalRepo(db);

  await repo.save({
    'user_id': 'u1',
    'email': 'tecnico@acme.com',
    'nome': 'Técnico Teste',
    'estatisticas': {'os_pendentes': 1, 'os_em_andamento': 0, 'os_concluidas_mes': 2}
  });

  final row = await repo.get();
  expect(row?['nome'], 'Técnico Teste');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: FAIL because repos and tables do not exist

- [ ] **Step 3: Add tables and repository implementations**

```dart
class EstoqueLocal extends Table {
  TextColumn get itemId => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get syncedAt => dateTime()();
  @override
  Set<Column> get primaryKey => {itemId};
}

class PerfilLocal extends Table {
  TextColumn get userId => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get syncedAt => dateTime()();
  @override
  Set<Column> get primaryKey => {userId};
}
```

- [ ] **Step 4: Regenerate drift code and run test**

Run: `dart run build_runner build --delete-conflicting-outputs`
Expected: PASS codegen

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/db/tables.dart apps/tecnico-mobile/lib/core/db/database.dart apps/tecnico-mobile/lib/core/db/database.g.dart apps/tecnico-mobile/lib/core/db/estoque_repo.dart apps/tecnico-mobile/lib/core/db/perfil_repo.dart apps/tecnico-mobile/test/core/db/offline_cache_test.dart
git commit -m "feat: add offline cache tables for estoque and perfil"
```

### Task 5: Migrar estoque para provider read-through offline

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/estoque/estoque_data.dart`
- Modify: `apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart`
- Test: `apps/tecnico-mobile/test/core/db/offline_cache_test.dart`

- [ ] **Step 1: Write the failing test for cached estoque fallback**

```dart
test('estoque provider serves cached snapshot when request fails', () async {
  final container = buildOfflineContainerWithCachedEstoque();
  final rows = await container.read(estoqueSaldoProvider.future);
  expect(rows.single.sku, 'CABO');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: FAIL because provider still calls API directly

- [ ] **Step 3: Implement read-through provider**

```dart
final estoqueSaldoProvider = FutureProvider<List<EstoqueLinha>>((ref) async {
  final repo = ref.watch(estoqueLocalRepoProvider);
  final cached = await repo.listAll();

  try {
    final dio = ref.watch(apiClientProvider);
    final r = await dio.get('/api/v1/tecnico/me/estoque/saldo');
    final linhas = ((r.data as Map<String, dynamic>)['linhas'] as List)
        .cast<Map<String, dynamic>>();
    await repo.replaceAll(linhas);
    return linhas.map(EstoqueLinha.fromJson).toList();
  } on DioException {
    if (cached.isNotEmpty) {
      return cached.map(EstoqueLinha.fromJson).toList();
    }
    rethrow;
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/estoque/estoque_data.dart apps/tecnico-mobile/lib/features/estoque/estoque_screen.dart apps/tecnico-mobile/test/core/db/offline_cache_test.dart
git commit -m "feat: add offline-first estoque provider"
```

### Task 6: Migrar perfil para provider read-through offline

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_data.dart`
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart`
- Test: `apps/tecnico-mobile/test/core/db/offline_cache_test.dart`

- [ ] **Step 1: Write the failing test for cached perfil fallback**

```dart
test('perfil provider serves cached snapshot when request fails', () async {
  final container = buildOfflineContainerWithCachedPerfil();
  final perfil = await container.read(perfilProvider.future);
  expect(perfil.nome, 'Técnico Teste');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: FAIL because provider still calls API directly

- [ ] **Step 3: Implement read-through provider**

```dart
final perfilProvider = FutureProvider<Perfil>((ref) async {
  final repo = ref.watch(perfilLocalRepoProvider);
  final cached = await repo.get();

  try {
    final dio = ref.watch(apiClientProvider);
    final r = await dio.get('/api/v1/tecnico/me/perfil');
    final map = r.data as Map<String, dynamic>;
    await repo.save(map);
    return Perfil.fromJson(map);
  } on DioException {
    if (cached != null) return Perfil.fromJson(cached);
    rethrow;
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/db/offline_cache_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/perfil/perfil_data.dart apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart apps/tecnico-mobile/test/core/db/offline_cache_test.dart
git commit -m "feat: add offline-first perfil provider"
```

### Task 7: Adicionar mutações otimistas no cache local de OS

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/db/os_repo.dart`
- Create: `apps/tecnico-mobile/test/core/db/os_repo_test.dart`

- [ ] **Step 1: Write the failing tests for optimistic updates**

```dart
test('markStartedOptimistic updates local status to em_andamento', () async {
  final db = testDatabase();
  final repo = OsLocalRepo(db);
  await repo.upsertOne(sampleOs(status: 'pendente'));

  await repo.markStartedOptimistic('os-1');

  final row = await repo.getById('os-1');
  expect(row?['status'], 'em_andamento');
});

test('markConcludedOptimistic updates local status to concluida', () async {
  final db = testDatabase();
  final repo = OsLocalRepo(db);
  await repo.upsertOne(sampleOs(status: 'em_andamento'));

  await repo.markConcludedOptimistic('os-1', const {'relatorio': 'ok'});

  final row = await repo.getById('os-1');
  expect(row?['status'], 'concluida');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/db/os_repo_test.dart`
Expected: FAIL because methods do not exist

- [ ] **Step 3: Implement optimistic mutation helpers**

```dart
Future<void> markStartedOptimistic(String id) async {
  final row = await getById(id);
  if (row == null) return;
  row['status'] = 'em_andamento';
  await upsertOne(row);
}

Future<void> markConcludedOptimistic(
  String id,
  Map<String, dynamic> payload,
) async {
  final row = await getById(id);
  if (row == null) return;
  row['status'] = 'concluida';
  row['concluida_em'] = DateTime.now().toIso8601String();
  row.addAll(payload);
  await upsertOne(row);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/db/os_repo_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/db/os_repo.dart apps/tecnico-mobile/test/core/db/os_repo_test.dart
git commit -m "feat: add optimistic local os updates"
```

### Task 8: Aplicar mutações otimistas nos fluxos de iniciar e concluir

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/os/os_detail_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/os/os_data.dart`
- Test: `apps/tecnico-mobile/test/core/db/os_repo_test.dart`

- [ ] **Step 1: Write the failing widget/integration test for offline status change**

```dart
testWidgets('offline iniciar updates screen state immediately', (tester) async {
  await pumpOfflineOsDetail(tester, status: 'pendente');

  await tester.tap(find.text('Iniciar visita (com GPS)'));
  await tester.pumpAndSettle();

  expect(find.text('Concluir OS'), findsOneWidget);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/db/os_repo_test.dart`
Expected: FAIL because UI still depends on server refresh

- [ ] **Step 3: Update screen flow to mutate cache before/when enqueueing**

```dart
await ref.read(osLocalRepoProvider).markStartedOptimistic(osId);
await svc.enqueue(
  osId: osId,
  kind: OutboxKind.iniciar,
  payload: body,
);
ref.invalidate(osDetailProvider(osId));
```

```dart
await ref.read(osLocalRepoProvider).markConcludedOptimistic(widget.osId, body);
await svc.enqueue(
  osId: widget.osId,
  kind: OutboxKind.concluir,
  payload: body,
);
widget.onDone();
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/db/os_repo_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/os/os_detail_screen.dart apps/tecnico-mobile/lib/features/os/os_data.dart apps/tecnico-mobile/test/core/db/os_repo_test.dart
git commit -m "feat: reflect offline os actions immediately in ui"
```

### Task 9: Expandir armazenamento de sessão para reentrada biométrica

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/auth/auth_storage.dart`
- Modify: `apps/tecnico-mobile/lib/core/auth/auth_repository.dart`
- Create: `apps/tecnico-mobile/lib/core/auth/session_state.dart`
- Create: `apps/tecnico-mobile/test/core/auth/session_state_test.dart`

- [ ] **Step 1: Write the failing test for saved reentry session**

```dart
test('session snapshot stores display name and biometric eligibility', () async {
  await saveSessionSnapshot(
    userId: 'u1',
    role: 'tecnico',
    nome: 'Roberto',
    biometricEnabled: true,
  );

  final session = await readSessionSnapshot();
  expect(session?.nome, 'Roberto');
  expect(session?.biometricEnabled, isTrue);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/auth/session_state_test.dart`
Expected: FAIL because snapshot API does not exist

- [ ] **Step 3: Implement session snapshot storage**

```dart
class SessionSnapshot {
  final String userId;
  final String role;
  final String nome;
  final bool biometricEnabled;
  const SessionSnapshot({
    required this.userId,
    required this.role,
    required this.nome,
    required this.biometricEnabled,
  });
}
```

```dart
Future<void> saveSessionSnapshot({
  required String userId,
  required String role,
  required String nome,
  required bool biometricEnabled,
}) async {
  await _storage.write(key: _kNome, value: nome);
  await _storage.write(key: _kBiometricEnabled, value: biometricEnabled ? '1' : '0');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/auth/session_state_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/auth/auth_storage.dart apps/tecnico-mobile/lib/core/auth/auth_repository.dart apps/tecnico-mobile/lib/core/auth/session_state.dart apps/tecnico-mobile/test/core/auth/session_state_test.dart
git commit -m "feat: persist session snapshot for biometric reentry"
```

### Task 10: Implementar serviço de biometria

**Files:**
- Create: `apps/tecnico-mobile/lib/core/auth/biometric_service.dart`
- Create: `apps/tecnico-mobile/test/core/auth/biometric_service_test.dart`

- [ ] **Step 1: Write the failing test for biometric availability contract**

```dart
test('biometric service reports unsupported when no hardware', () async {
  final service = FakeBiometricService(
    canCheckBiometrics: false,
    isDeviceSupported: false,
  );

  expect(await service.canUseBiometrics(), isFalse);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/auth/biometric_service_test.dart`
Expected: FAIL because service does not exist

- [ ] **Step 3: Implement local_auth wrapper**

```dart
class BiometricService {
  final LocalAuthentication _auth;
  BiometricService(this._auth);

  Future<bool> canUseBiometrics() async {
    return await _auth.canCheckBiometrics && await _auth.isDeviceSupported();
  }

  Future<bool> authenticate() {
    return _auth.authenticate(
      localizedReason: 'Entrar com Face ID',
      options: const AuthenticationOptions(
        biometricOnly: true,
        stickyAuth: true,
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/auth/biometric_service_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/auth/biometric_service.dart apps/tecnico-mobile/test/core/auth/biometric_service_test.dart apps/tecnico-mobile/pubspec.yaml
git commit -m "feat: add biometric auth service"
```

### Task 11: Adicionar tela curta de reentrada e bootstrap de sessão

**Files:**
- Create: `apps/tecnico-mobile/lib/features/auth/reentry_screen.dart`
- Modify: `apps/tecnico-mobile/lib/router.dart`
- Modify: `apps/tecnico-mobile/lib/main.dart`
- Modify: `apps/tecnico-mobile/lib/features/splash/splash_screen.dart`
- Create: `apps/tecnico-mobile/test/features/auth/reentry_screen_test.dart`

- [ ] **Step 1: Write the failing widget test for reentry screen**

```dart
testWidgets('reentry screen shows technician name and Face ID action', (tester) async {
  await tester.pumpWidget(buildReentryApp(nome: 'Roberto'));

  expect(find.text('Roberto'), findsOneWidget);
  expect(find.text('Entrar com Face ID'), findsOneWidget);
  expect(find.text('Entrar com email e senha'), findsOneWidget);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/reentry_screen_test.dart`
Expected: FAIL because screen and route do not exist

- [ ] **Step 3: Implement route gating and reentry screen**

```dart
GoRoute(path: '/reentry', builder: (_, __) => const ReentryScreen()),
```

```dart
if (hasToken && hasBiometricSession) {
  context.go('/reentry');
} else {
  context.go('/os');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/reentry_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/auth/reentry_screen.dart apps/tecnico-mobile/lib/router.dart apps/tecnico-mobile/lib/main.dart apps/tecnico-mobile/lib/features/splash/splash_screen.dart apps/tecnico-mobile/test/features/auth/reentry_screen_test.dart
git commit -m "feat: add biometric reentry screen"
```

### Task 12: Redesenhar login na direção visual A

**Files:**
- Modify: `apps/tecnico-mobile/lib/features/auth/login_screen.dart`
- Test: `apps/tecnico-mobile/test/features/auth/reentry_screen_test.dart`

- [ ] **Step 1: Write the failing widget test for premium login structure**

```dart
testWidgets('login screen renders premium hero and primary card', (tester) async {
  await tester.pumpWidget(buildLoginApp());

  expect(find.text('Bem-vindo'), findsOneWidget);
  expect(find.text('Entrar'), findsOneWidget);
  expect(find.byType(TextField), findsNWidgets(2));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/features/auth/reentry_screen_test.dart`
Expected: FAIL because updated expectations are not met yet

- [ ] **Step 3: Implement visual redesign**

```dart
return Scaffold(
  body: DecoratedBox(
    decoration: const BoxDecoration(
      gradient: LinearGradient(
        colors: [Color(0xFF08111F), Color(0xFF0F2037), Color(0xFF173D2D)],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ),
    ),
    child: ...
  ),
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/features/auth/reentry_screen_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/features/auth/login_screen.dart apps/tecnico-mobile/test/features/auth/reentry_screen_test.dart
git commit -m "feat: redesign tecnico mobile login"
```

### Task 13: Invalidar sessão em 401 e limpar tudo no logout

**Files:**
- Modify: `apps/tecnico-mobile/lib/core/api/api_client.dart`
- Modify: `apps/tecnico-mobile/lib/core/auth/auth_storage.dart`
- Modify: `apps/tecnico-mobile/lib/features/os/os_list_screen.dart`
- Modify: `apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/estoque_repo.dart`
- Modify: `apps/tecnico-mobile/lib/core/db/perfil_repo.dart`
- Modify: `apps/tecnico-mobile/lib/core/sync/outbox_repo.dart`
- Create: `apps/tecnico-mobile/test/core/auth/session_state_test.dart`

- [ ] **Step 1: Write the failing test for full local cleanup**

```dart
test('clear session removes auth, biometric snapshot, cache and outbox', () async {
  final db = testDatabase();
  await seedAllLocalData(db);

  await clearLocalSessionData(db);

  expect(await readAccessToken(), isNull);
  expect(await db.select(db.outboxItem).get(), isEmpty);
  expect(await db.select(db.osLocal).get(), isEmpty);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/core/auth/session_state_test.dart`
Expected: FAIL because unified cleanup does not exist

- [ ] **Step 3: Implement cleanup and 401 invalidation path**

```dart
Future<void> clearLocalSessionData(AppDatabase db) async {
  await clearAuth();
  await db.delete(db.outboxItem).go();
  await db.delete(db.osLocal).go();
  await db.delete(db.estoqueLocal).go();
  await db.delete(db.perfilLocal).go();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/core/auth/session_state_test.dart`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/lib/core/api/api_client.dart apps/tecnico-mobile/lib/core/auth/auth_storage.dart apps/tecnico-mobile/lib/features/os/os_list_screen.dart apps/tecnico-mobile/lib/features/perfil/perfil_screen.dart apps/tecnico-mobile/lib/core/db/estoque_repo.dart apps/tecnico-mobile/lib/core/db/perfil_repo.dart apps/tecnico-mobile/lib/core/sync/outbox_repo.dart apps/tecnico-mobile/test/core/auth/session_state_test.dart
git commit -m "fix: clear local session state on logout and 401"
```

### Task 14: Atualizar README e validar o fluxo completo

**Files:**
- Modify: `apps/tecnico-mobile/README.md`
- Modify: `apps/tecnico-mobile/test/widget_test.dart`
- Modify: `apps/tecnico-mobile/test/smoke_test.dart`

- [ ] **Step 1: Write the failing smoke/widget assertions for real app behavior**

```dart
testWidgets('app boots to login or reentry instead of placeholder', (tester) async {
  expect(find.text('placeholder'), findsNothing);
});
```

- [ ] **Step 2: Run tests to verify current gaps**

Run: `flutter test`
Expected: FAIL in new widget coverage until app boot assertions are wired

- [ ] **Step 3: Replace placeholder tests and update README**

```md
- [x] Drift DB com OS cached + outbox table
- [x] Sync service com retry baseado na última tentativa
- [x] Estoque do técnico com cache local
- [x] Perfil com cache local
- [x] Reentrada com Face ID no iOS após primeiro login
```

- [ ] **Step 4: Run final verification**

Run: `dart run build_runner build --delete-conflicting-outputs`
Expected: PASS

Run: `flutter analyze`
Expected: PASS with no new warnings beyond accepted baseline

Run: `flutter test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/tecnico-mobile/README.md apps/tecnico-mobile/test/widget_test.dart apps/tecnico-mobile/test/smoke_test.dart apps/tecnico-mobile/lib
git commit -m "docs: update tecnico mobile offline and login behavior"
```
