import 'package:drift/native.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/db/estoque_repo.dart';
import 'package:tecnico_mobile/core/db/perfil_repo.dart';
import 'package:tecnico_mobile/core/db/os_repo.dart';
import 'package:tecnico_mobile/core/db/cliente_cadastro_repo.dart';
import 'package:tecnico_mobile/core/api/api_client.dart';
import 'package:tecnico_mobile/features/estoque/estoque_data.dart';
import 'package:tecnico_mobile/features/perfil/perfil_data.dart';
import 'package:tecnico_mobile/features/os/os_data.dart';
import 'package:tecnico_mobile/features/clientes/cliente_data.dart';

AppDatabase testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

Map<String, dynamic> _osRow({
  required String id,
  required String codigo,
  required String status,
}) {
  return {
    'id': id,
    'codigo': codigo,
    'status': status,
    'problema': 'Sem sinal',
    'endereco': 'Rua A, 100',
    'nome_cliente': 'Cliente $id',
    'criada_em': DateTime(2026, 5, 20).toUtc().toIso8601String(),
  };
}

Map<String, dynamic> _clienteRow({
  required String id,
  required String nome,
  String? neighborhood,
  String? serial,
  DateTime? sgpSyncedAt,
}) {
  return {
    'id': id,
    'cpf': '12345678901',
    'nome': nome,
    'address': 'Rua das Palmeiras',
    'number': '120',
    'neighborhood': neighborhood ?? 'Centro',
    'city': 'Manaus',
    'plan_nome': 'Fibra 500 Mega',
    'installer_nome': 'Técnico 1',
    'serial': serial,
    'sgp_synced_at': sgpSyncedAt?.toUtc().toIso8601String(),
    'sgp_id': sgpSyncedAt == null ? null : 'sgp-$id',
    'created_at': DateTime(2026, 5, 20).toUtc().toIso8601String(),
  };
}

void main() {
  test('estoque repo round-trips cached rows', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );

    final rows = await repo.listAll(userId: 'u1');
    expect(rows.single['sku'], 'CABO');
  });

  test('perfil repo returns cached snapshot for requested user id', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = PerfilLocalRepo(db);

    await repo.save({
      'user_id': 'u1',
      'email': 'tecnico@acme.com',
      'nome': 'Tecnico Teste',
      'estatisticas': {
        'os_pendentes': 1,
        'os_em_andamento': 0,
        'os_concluidas_mes': 2,
      },
    });

    await repo.save({
      'user_id': 'u2',
      'email': 'outra@acme.com',
      'nome': 'Outra Pessoa',
      'estatisticas': {
        'os_pendentes': 9,
        'os_em_andamento': 4,
        'os_concluidas_mes': 1,
      },
    });

    final row = await repo.get(userId: 'u1');
    expect(row?['nome'], 'Tecnico Teste');
  });

  test('estoque repo clear removes only requested user snapshot', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        {
          'item_id': '9',
          'sku': 'FIBRA',
          'nome': 'Fibra',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 7,
        },
      ],
    );

    await repo.clear(userId: 'u1');

    expect(await repo.listAll(userId: 'u1'), isEmpty);
    expect((await repo.listAll(userId: 'u2')).single['sku'], 'FIBRA');
  });

  test('estoque repo keeps snapshots isolated when multiple users coexist',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);

    await repo.replaceAll(
      userId: 'u1',
      rows: [
        {
          'item_id': '1',
          'sku': 'CABO',
          'nome': 'Cabo',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 3,
        },
      ],
    );
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        {
          'item_id': '2',
          'sku': 'FIBRA',
          'nome': 'Fibra',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 7,
        },
      ],
    );

    final rows = await repo.listAll(userId: 'u1');

    expect(rows, hasLength(1));
    expect(rows.single['sku'], 'CABO');
    expect(rows.single['item_id'], '1');
  });

  test(
    'estoque provider serves cached snapshot for current auth user when offline',
    () async {
      final db = testDatabase();
      addTearDown(db.close);

      final repo = EstoqueLocalRepo(db);
      await repo.replaceAll(
        userId: 'u1',
        rows: [
          {
            'item_id': '1',
            'sku': 'CABO',
            'nome': 'Cabo U1',
            'categoria': 'Rede',
            'serializado': false,
            'saldo': 3,
          },
        ],
      );
      await repo.replaceAll(
        userId: 'u2',
        rows: [
          {
            'item_id': '2',
            'sku': 'FIBRA',
            'nome': 'Fibra U2',
            'categoria': 'Rede',
            'serializado': false,
            'saldo': 7,
          },
        ],
      );

      final container = ProviderContainer(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith((ref) => _offlineDio()),
          estoqueReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
        ],
      );
      addTearDown(container.dispose);

      final rows = await container.read(estoqueSaldoProvider.future);

      expect(rows, hasLength(1));
      expect(rows.single.sku, 'FIBRA');
      expect(rows.single.nome, 'Fibra U2');
    },
  );

  test('estoque provider propagates error when request fails without cache',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
        estoqueReadUserIdProvider.overrideWith((ref) => () async => 'u9'),
      ],
    );
    addTearDown(container.dispose);

    await expectLater(
      container.read(estoqueSaldoProvider.future),
      throwsA(isA<DioException>()),
    );
  });

  test('estoque provider does not use cache on 401 response', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = EstoqueLocalRepo(db);
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        {
          'item_id': '2',
          'sku': 'FIBRA',
          'nome': 'Fibra U2',
          'categoria': 'Rede',
          'serializado': false,
          'saldo': 7,
        },
      ],
    );

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _unauthorizedDio()),
        estoqueReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
      ],
    );
    addTearDown(container.dispose);

    await expectLater(
      container.read(estoqueSaldoProvider.future),
      throwsA(
        isA<DioException>().having(
          (e) => e.response?.statusCode,
          'statusCode',
          401,
        ),
      ),
    );
  });

  test('os list provider serves cached snapshot when offline', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = OsLocalRepo(db);
    await repo.upsertAll([
      _osRow(id: 'os-1', codigo: 'OS-001', status: 'pendente'),
    ]);

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
      ],
    );
    addTearDown(container.dispose);

    final rows = await container.read(osListStreamProvider.future);

    expect(rows, hasLength(1));
    expect(rows.single['codigo'], 'OS-001');
  });

  test('os list provider propagates error on cold start offline without cache',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
      ],
    );
    addTearDown(container.dispose);

    await expectLater(
      container.read(osListStreamProvider.future),
      throwsA(isA<DioException>()),
    );
  });

  test('clientes list provider serves cached snapshot when offline', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = ClienteCadastroLocalRepo(db);
    await repo.replaceAll(
      userId: 'u1',
      rows: [
        _clienteRow(id: 'cliente-1', nome: 'Cliente U1'),
      ],
    );
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        _clienteRow(id: 'cliente-2', nome: 'Cliente U2'),
      ],
    );

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
        clienteReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
      ],
    );
    addTearDown(container.dispose);

    final page = await container.read(clientesListProvider.future);

    expect(page.items, hasLength(1));
    expect(page.items.single.id, 'cliente-2');
    expect(page.items.single.nome, 'Cliente U2');
  });

  test(
    'clientes list provider propagates error when request fails without cache',
    () async {
      final db = testDatabase();
      addTearDown(db.close);

      final container = ProviderContainer(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith((ref) => _offlineDio()),
          clienteReadUserIdProvider.overrideWith((ref) => () async => 'u9'),
        ],
      );
      addTearDown(container.dispose);

      await expectLater(
        container.read(clientesListProvider.future),
        throwsA(isA<DioException>()),
      );
    },
  );

  test(
    'cliente detail provider opens offline from cached list snapshot only',
    () async {
      final db = testDatabase();
      addTearDown(db.close);

      final repo = ClienteCadastroLocalRepo(db);
      await repo.replaceAll(
        userId: 'u2',
        rows: [
          _clienteRow(
            id: 'cliente-2',
            nome: 'Cliente U2',
            serial: 'ONU-999',
          ),
        ],
      );

      final container = ProviderContainer(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith((ref) => _offlineDio()),
          clienteReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
        ],
      );
      addTearDown(container.dispose);

      final cliente =
          await container.read(clienteDetailProvider('cliente-2').future);

      expect(cliente.id, 'cliente-2');
      expect(cliente.nome, 'Cliente U2');
      expect(cliente.address, 'Rua das Palmeiras');
      expect(cliente.serial, 'ONU-999');
      expect(cliente.planNome, 'Fibra 500 Mega');
    },
  );

  test('clientes offline fallback honors sgp status and serial search',
      () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = ClienteCadastroLocalRepo(db);
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        _clienteRow(
          id: 'cliente-1',
          nome: 'Marina Silva',
          neighborhood: 'Centro',
          serial: 'ONU-123456',
          sgpSyncedAt: DateTime(2026, 5, 19),
        ),
        _clienteRow(
          id: 'cliente-2',
          nome: 'Carlos Souza',
          neighborhood: 'Flores',
          serial: 'ONU-999999',
        ),
      ],
    );

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
        clienteReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
        clienteListFilterProvider.overrideWith(
          (ref) => const ClienteListFilter(
            q: 'onu-123456',
            sgpStatus: 'synced',
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    final serialAndSgp = await container.read(clientesListProvider.future);
    expect(serialAndSgp.items, hasLength(1));
    expect(serialAndSgp.items.single.id, 'cliente-1');
  });

  test('clientes offline fallback honors neighborhood search', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = ClienteCadastroLocalRepo(db);
    await repo.replaceAll(
      userId: 'u2',
      rows: [
        _clienteRow(
          id: 'cliente-1',
          nome: 'Marina Silva',
          neighborhood: 'Centro',
          serial: 'ONU-123456',
          sgpSyncedAt: DateTime(2026, 5, 19),
        ),
        _clienteRow(
          id: 'cliente-2',
          nome: 'Carlos Souza',
          neighborhood: 'Flores',
          serial: 'ONU-999999',
        ),
      ],
    );

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _offlineDio()),
        clienteReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
        clienteListFilterProvider.overrideWith(
          (ref) => const ClienteListFilter(
            q: 'flores',
            sgpStatus: 'pending',
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    final neighborhoodPending =
        await container.read(clientesListProvider.future);
    expect(neighborhoodPending.items, hasLength(1));
    expect(neighborhoodPending.items.single.id, 'cliente-2');
  });

  test(
    'perfil provider serves cached snapshot for current auth user when offline',
    () async {
      final db = testDatabase();
      addTearDown(db.close);

      final repo = PerfilLocalRepo(db);
      await repo.save({
        'user_id': 'u1',
        'email': 'u1@acme.com',
        'nome': 'Tecnico U1',
        'estatisticas': {
          'os_pendentes': 1,
          'os_em_andamento': 0,
          'os_concluidas_mes': 2,
        },
      });
      await repo.save({
        'user_id': 'u2',
        'email': 'u2@acme.com',
        'nome': 'Tecnico Teste',
        'estatisticas': {
          'os_pendentes': 4,
          'os_em_andamento': 1,
          'os_concluidas_mes': 6,
        },
      });

      final container = ProviderContainer(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith((ref) => _offlineDio()),
          perfilReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
        ],
      );
      addTearDown(container.dispose);

      final perfil = await container.read(perfilProvider.future);

      expect(perfil.userId, 'u2');
      expect(perfil.nome, 'Tecnico Teste');
      expect(perfil.email, 'u2@acme.com');
    },
  );

  test(
    'perfil provider saves online snapshot under current auth user id',
    () async {
      final db = testDatabase();
      addTearDown(db.close);

      final repo = PerfilLocalRepo(db);
      final container = ProviderContainer(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith(
            (ref) => _successfulPerfilDio({
              'email': 'api@acme.com',
              'nome': 'Perfil API',
              'user_id': 'wrong-user',
              'estatisticas': {
                'os_pendentes': 2,
                'os_em_andamento': 1,
                'os_concluidas_mes': 9,
              },
            }),
          ),
          perfilReadUserIdProvider
              .overrideWith((ref) => () async => 'u-current'),
        ],
      );
      addTearDown(container.dispose);

      final perfil = await container.read(perfilProvider.future);
      final cached = await repo.get(userId: 'u-current');

      expect(perfil.userId, 'u-current');
      expect(perfil.nome, 'Perfil API');
      expect(cached, isNotNull);
      expect(cached?['user_id'], 'u-current');
      expect(await repo.get(userId: 'wrong-user'), isNull);
    },
  );

  test('perfil provider does not use cache on 401 response', () async {
    final db = testDatabase();
    addTearDown(db.close);

    final repo = PerfilLocalRepo(db);
    await repo.save({
      'user_id': 'u2',
      'email': 'u2@acme.com',
      'nome': 'Tecnico Teste',
      'estatisticas': {
        'os_pendentes': 4,
        'os_em_andamento': 1,
        'os_concluidas_mes': 6,
      },
    });

    final container = ProviderContainer(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => _unauthorizedDio()),
        perfilReadUserIdProvider.overrideWith((ref) => () async => 'u2'),
      ],
    );
    addTearDown(container.dispose);

    await expectLater(
      container.read(perfilProvider.future),
      throwsA(
        isA<DioException>().having(
          (e) => e.response?.statusCode,
          'statusCode',
          401,
        ),
      ),
    );
  });
}

Dio _offlineDio() {
  final dio = Dio();
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        handler.reject(
          DioException(
            requestOptions: options,
            type: DioExceptionType.connectionError,
            error: 'offline',
          ),
        );
      },
    ),
  );
  return dio;
}

Dio _successfulPerfilDio(Map<String, dynamic> payload) {
  final dio = Dio();
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        handler.resolve(
          Response(
            requestOptions: options,
            statusCode: 200,
            data: payload,
          ),
        );
      },
    ),
  );
  return dio;
}

Dio _unauthorizedDio() {
  final dio = Dio();
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        handler.reject(
          DioException(
            requestOptions: options,
            response: Response(
              requestOptions: options,
              statusCode: 401,
            ),
            type: DioExceptionType.badResponse,
          ),
        );
      },
    ),
  );
  return dio;
}
