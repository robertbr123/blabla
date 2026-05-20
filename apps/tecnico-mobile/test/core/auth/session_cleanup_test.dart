import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/auth/auth_state.dart';
import 'package:tecnico_mobile/core/auth/auth_storage.dart';
import 'package:tecnico_mobile/core/auth/session_cleanup.dart';
import 'package:tecnico_mobile/core/db/cliente_cadastro_repo.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/db/estoque_repo.dart';
import 'package:tecnico_mobile/core/db/os_repo.dart';
import 'package:tecnico_mobile/core/db/perfil_repo.dart';
import 'package:tecnico_mobile/core/sync/outbox_repo.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('clearLocalSession removes auth, caches and outbox', () async {
    final db = testDatabase();
    final osRepo = OsLocalRepo(db);
    final estoqueRepo = EstoqueLocalRepo(db);
    final perfilRepo = PerfilLocalRepo(db);
    final clienteRepo = ClienteCadastroLocalRepo(db);
    final outboxRepo = OutboxRepo(db);

    await writeAccessToken('token-1');
    await writeUser(userId: 'u1', role: 'tecnico');
    await saveSessionSnapshot(
      userId: 'u1',
      role: 'tecnico',
      nome: 'Roberto',
      biometricEnabled: true,
    );

    await osRepo.upsertOne({
      'id': 'os-1',
      'codigo': 'OS-1',
      'status': 'pendente',
      'problema': 'Sem sinal',
      'endereco': 'Rua A',
      'criada_em': '2026-05-19T12:00:00Z',
    });
    await estoqueRepo.replaceAll(userId: 'u1', rows: [
      {
        'item_id': '1',
        'sku': 'CABO',
        'nome': 'Cabo',
        'categoria': 'Rede',
        'serializado': false,
        'saldo': 3,
      },
    ]);
    await perfilRepo.save({
      'user_id': 'u1',
      'email': 'roberto@empresa.com',
      'nome': 'Roberto',
      'estatisticas': {
        'os_pendentes': 1,
        'os_em_andamento': 0,
        'os_concluidas_mes': 2,
      },
    });
    await clienteRepo.replaceAll(userId: 'u1', rows: [
      {
        'id': 'c1',
        'nome': 'Cliente 1',
        'city': 'Rio Branco',
        'plan_nome': 'Fibra',
      },
    ]);
    await outboxRepo.enqueue(
      osId: 'os-1',
      kind: OutboxKind.iniciar,
      payload: const {'lat': 1},
    );

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
      ],
    );
    addTearDown(container.dispose);
    addTearDown(db.close);

    await container.read(sessionCleanupProvider).clearLocalSession();

    expect(await readAccessToken(), isNull);
    expect(await readUserId(), isNull);
    expect(await readRole(), isNull);
    expect(await readSessionSnapshot(), isNull);
    expect(await osRepo.listAll(), isEmpty);
    expect(await estoqueRepo.listAll(userId: 'u1'), isEmpty);
    expect(await perfilRepo.get(userId: 'u1'), isNull);
    expect(await clienteRepo.listAll(userId: 'u1'), isEmpty);
    expect(await outboxRepo.pendingCount(), 0);
    expect(await container.read(hasTokenProvider.future), isFalse);
    expect(await container.read(sessionSnapshotProvider.future), isNull);
  });
}
