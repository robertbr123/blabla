import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:permission_handler_platform_interface/permission_handler_platform_interface.dart';
import 'package:tecnico_mobile/core/api/api_client.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';
import 'package:tecnico_mobile/features/os/os_detail_screen.dart';

class _FakeConnectivityPlatform extends ConnectivityPlatform {
  _FakeConnectivityPlatform(this.results);

  final List<ConnectivityResult> results;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async => results;

  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      Stream<List<ConnectivityResult>>.value(results);
}

class _FakePermissionHandlerPlatform extends PermissionHandlerPlatform {
  _FakePermissionHandlerPlatform(this.status);

  final PermissionStatus status;

  @override
  Future<PermissionStatus> checkPermissionStatus(Permission permission) async {
    return status;
  }

  @override
  Future<ServiceStatus> checkServiceStatus(Permission permission) async {
    return ServiceStatus.disabled;
  }

  @override
  Future<bool> openAppSettings() async => true;

  @override
  Future<Map<Permission, PermissionStatus>> requestPermissions(
    List<Permission> permissions,
  ) async {
    return {
      for (final permission in permissions) permission: status,
    };
  }

  @override
  Future<bool> shouldShowRequestPermissionRationale(
    Permission permission,
  ) async {
    return false;
  }
}

AppDatabase _testDatabase() => AppDatabase.forTesting(NativeDatabase.memory());

Dio _offlineDio() {
  final dio = Dio();
  dio.httpClientAdapter = _OfflineAdapter();
  return dio;
}

class _OfflineAdapter implements HttpClientAdapter {
  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) {
    throw DioException(
      requestOptions: options,
      type: DioExceptionType.connectionError,
      error: 'offline',
    );
  }
}

Future<void> _pumpOfflineOsDetail(
  WidgetTester tester, {
  required AppDatabase db,
  required String status,
  Dio? dio,
}) async {
  await db.into(db.osLocal).insert(
        OsLocalCompanion.insert(
          id: 'os-1',
          codigo: 'OS-001',
          status: status,
          problema: 'Sem sinal',
          endereco: 'Rua A, 100',
          nomeCliente: const Value('Cliente Teste'),
          agendamentoAt: const Value('2026-05-19T09:00:00Z'),
          criadaEm: '2026-05-18T12:00:00Z',
          concluidaEm: const Value(null),
          payloadJson:
              '{"id":"os-1","codigo":"OS-001","status":"$status","problema":"Sem sinal","endereco":"Rua A, 100","nome_cliente":"Cliente Teste","agendamento_at":"2026-05-19T09:00:00Z","criada_em":"2026-05-18T12:00:00Z","concluida_em":null}',
          syncedAt: DateTime.now(),
        ),
      );

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        dbProvider.overrideWith((ref) => db),
        apiClientProvider.overrideWith((ref) => dio ?? _offlineDio()),
        pendingCountProvider.overrideWith((ref) => Stream<int>.value(0)),
      ],
      child: const MaterialApp(home: OsDetailScreen(id: 'os-1')),
    ),
  );

  await tester.pumpAndSettle();
}

Future<void> _scrollUntilVisible(WidgetTester tester, Finder finder) async {
  await tester.dragUntilVisible(
    finder,
    find.byType(Scrollable).first,
    const Offset(0, -240),
  );
  await tester.pumpAndSettle();
}

Future<void> _scrollBackUntilVisible(WidgetTester tester, Finder finder) async {
  await tester.dragUntilVisible(
    finder,
    find.byType(Scrollable).first,
    const Offset(0, 240),
  );
  await tester.pumpAndSettle();
}

void main() {
  late ConnectivityPlatform originalConnectivityPlatform;
  late PermissionHandlerPlatform originalPermissionPlatform;

  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    originalConnectivityPlatform = ConnectivityPlatform.instance;
    originalPermissionPlatform = PermissionHandlerPlatform.instance;
  });

  setUp(() {
    PermissionHandlerPlatform.instance =
        _FakePermissionHandlerPlatform(PermissionStatus.denied);
  });

  tearDown(() {
    ConnectivityPlatform.instance = originalConnectivityPlatform;
    PermissionHandlerPlatform.instance = originalPermissionPlatform;
  });

  testWidgets('offline iniciar updates screen state immediately',
      (tester) async {
    final db = _testDatabase();
    addTearDown(db.close);

    ConnectivityPlatform.instance =
        _FakeConnectivityPlatform(const [ConnectivityResult.none]);
    await _pumpOfflineOsDetail(
      tester,
      db: db,
      status: 'pendente',
    );

    expect(find.text('Iniciar visita (com GPS)'), findsOneWidget);
    expect(find.text('Concluir OS'), findsNothing);

    await _scrollUntilVisible(
      tester,
      find.text('Iniciar visita (com GPS)'),
    );
    await tester.tap(find.text('Iniciar visita (com GPS)'));
    await tester.pumpAndSettle();

    expect(find.text('Iniciar visita (com GPS)'), findsNothing);
    expect(find.text('Concluir OS'), findsOneWidget);
  });

  testWidgets('os detail groups actions and context in separate sections',
      (tester) async {
    final db = _testDatabase();
    addTearDown(db.close);

    ConnectivityPlatform.instance =
        _FakeConnectivityPlatform(const [ConnectivityResult.none]);
    await _pumpOfflineOsDetail(
      tester,
      db: db,
      status: 'em_andamento',
    );

    expect(find.textContaining('Status'), findsOneWidget);
    await _scrollUntilVisible(tester, find.text('Fotos'));
    expect(find.textContaining('Fotos'), findsOneWidget);
    expect(find.textContaining('Ações'), findsOneWidget);
  });

  testWidgets('offline concluir updates screen state immediately',
      (tester) async {
    final db = _testDatabase();
    addTearDown(db.close);

    ConnectivityPlatform.instance =
        _FakeConnectivityPlatform(const [ConnectivityResult.none]);
    await _pumpOfflineOsDetail(
      tester,
      db: db,
      status: 'em_andamento',
    );

    expect(find.text('Concluir OS'), findsOneWidget);

    await _scrollUntilVisible(tester, find.text('Concluir OS'));
    await tester.tap(find.text('Concluir OS'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Concluir'));
    await tester.pumpAndSettle();
    await _scrollBackUntilVisible(tester, find.text('Concluída'));

    expect(find.text('Concluir OS'), findsNothing);
    expect(find.text('Iniciar visita (com GPS)'), findsNothing);
    expect(find.text('Concluída'), findsOneWidget);
    expect(
      find.text('Sem conexão — conclusão enfileirada pra envio depois.'),
      findsOneWidget,
    );
  });

  testWidgets(
      'online iniciar fallback updates screen state immediately when post fails',
      (tester) async {
    final db = _testDatabase();
    addTearDown(db.close);

    ConnectivityPlatform.instance =
        _FakeConnectivityPlatform(const [ConnectivityResult.wifi]);
    await _pumpOfflineOsDetail(
      tester,
      db: db,
      status: 'pendente',
    );

    await _scrollUntilVisible(
      tester,
      find.text('Iniciar visita (com GPS)'),
    );
    await tester.tap(find.text('Iniciar visita (com GPS)'));
    await tester.pumpAndSettle();

    expect(find.text('Iniciar visita (com GPS)'), findsNothing);
    expect(find.text('Concluir OS'), findsOneWidget);
  });

  testWidgets(
      'online concluir fallback updates screen state immediately when post fails',
      (tester) async {
    final db = _testDatabase();
    addTearDown(db.close);

    ConnectivityPlatform.instance =
        _FakeConnectivityPlatform(const [ConnectivityResult.wifi]);
    await _pumpOfflineOsDetail(
      tester,
      db: db,
      status: 'em_andamento',
    );

    await _scrollUntilVisible(tester, find.text('Concluir OS'));
    await tester.tap(find.text('Concluir OS'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Concluir'));
    await tester.pumpAndSettle();
    await _scrollBackUntilVisible(tester, find.text('Concluída'));

    expect(find.text('Concluir OS'), findsNothing);
    expect(find.text('Concluída'), findsOneWidget);
    expect(
      find.text('Falha online — conclusão enfileirada pra retry.'),
      findsOneWidget,
    );
  });
}
