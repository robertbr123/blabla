import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:drift/native.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:tecnico_mobile/core/api/api_client.dart';
import 'package:tecnico_mobile/core/db/database.dart';
import 'package:tecnico_mobile/core/location/location_service.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';
import 'package:tecnico_mobile/features/clientes/cliente_data.dart';
import 'package:tecnico_mobile/features/clientes/cliente_detail_screen.dart';
import 'package:tecnico_mobile/features/clientes/cliente_form_data.dart';
import 'package:tecnico_mobile/features/clientes/cliente_novo_screen.dart';
import 'package:tecnico_mobile/features/clientes/clientes_list_screen.dart';
import 'package:tecnico_mobile/features/clientes/widgets/cliente_card.dart';
import 'package:tecnico_mobile/features/estoque/estoque_data.dart';

const _permissionChannel = MethodChannel(
  'flutter.baseflow.com/permissions/methods',
);

ClienteListItem _listItem({
  required String id,
  required String nome,
  DateTime? sgpSyncedAt,
}) {
  return ClienteListItem(
    id: id,
    cpf: '12345678901',
    nome: nome,
    address: 'Rua das Palmeiras',
    number: '120',
    neighborhood: 'Centro',
    city: 'Manaus',
    planNome: 'Fibra 500 Mega',
    installerNome: 'Técnico 1',
    sgpSyncedAt: sgpSyncedAt,
    sgpId: sgpSyncedAt == null ? null : 'sgp-$id',
    createdAt: DateTime(2026, 5, 20),
  );
}

ClienteCampo _cliente() {
  return ClienteCampo(
    id: 'cliente-1',
    cpf: '12345678901',
    nome: 'Marina Silva',
    dob: DateTime(1992, 4, 10),
    telefone: '92999998888',
    email: 'marina@example.com',
    cep: '69000000',
    address: 'Rua das Palmeiras',
    number: '120',
    complement: 'Apto 12',
    neighborhood: 'Centro',
    city: 'Manaus',
    state: 'AM',
    planId: 1,
    planNome: 'Fibra 500 Mega',
    pppoeUser: 'marina.silva',
    pppoePass: 'senha123',
    dueDate: 20,
    installerUserId: 'tech-1',
    installerNome: 'Técnico 1',
    serial: 'ONU-123456',
    contrato: 'CTR-001',
    observation: 'Cliente prefere contato por WhatsApp.',
    latitude: -3.1019,
    longitude: -60.025,
    locationAccuracy: 12,
    fotos: const [],
    registrationDate: DateTime(2026, 5, 12),
    sgpSyncedAt: DateTime(2026, 5, 19),
    sgpId: 'sgp-1',
    createdAt: DateTime(2026, 5, 12),
    updatedAt: DateTime(2026, 5, 20),
  );
}

Future<void> pumpClientesList(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        clientesListProvider.overrideWith(
          (ref) async => ClienteListPage(
            items: [
              _listItem(
                id: 'cliente-1',
                nome: 'Marina Silva',
                sgpSyncedAt: DateTime(2026, 5, 19),
              ),
              _listItem(id: 'cliente-2', nome: 'Carlos Souza'),
            ],
          ),
        ),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: const ClientesListScreen(),
      ),
    ),
  );

  await tester.pumpAndSettle();
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

Future<void> pumpClienteDetail(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        clienteDetailProvider('cliente-1').overrideWith((ref) async {
          return _cliente();
        }),
        clienteOsHistoricoProvider('cliente-1').overrideWith((ref) async {
          return [
            ClienteOsHistorico(
              id: 'os-1',
              codigo: 'OS-100',
              status: 'concluida',
              problema: 'Sem sinal',
              criadaEm: DateTime(2026, 5, 18),
              concluidaEm: DateTime(2026, 5, 19),
            ),
          ];
        }),
        clienteMateriaisProvider('cliente-1').overrideWith((ref) async {
          return const <MaterialUsado>[];
        }),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: const ClienteDetailScreen(id: 'cliente-1'),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

Future<void> pumpNovoCliente(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        locationServiceProvider.overrideWith(
          (ref) => _FakeLocationService(
            LocationResult(-3.1019, -60.025, 12),
          ),
        ),
        planosProvider.overrideWith((ref) async {
          return [
            SgpPlano(
              id: 1,
              grupo: 'Fibra',
              descricao: 'Fibra 500 Mega',
              preco: 129.9,
              download: 512000,
              upload: 256000,
            ),
          ];
        }),
        estoqueSaldoProvider.overrideWith((ref) async {
          return [
            EstoqueLinha(
              itemId: 'item-1',
              sku: 'ONU-01',
              nome: 'ONU Wi-Fi 6',
              categoria: 'ONU',
              serializado: true,
              saldo: 2,
            ),
          ];
        }),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: const ClienteNovoScreen(),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

class _FakeLocationService implements LocationService {
  _FakeLocationService(this.result);

  final LocationResult? result;

  @override
  Future<LocationResult?> capture() async => result;
}

Future<void> pumpClienteCardDarkTheme(WidgetTester tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: buildDarkTheme(),
      home: Scaffold(
        body: ClienteCard(
          item: _listItem(id: 'cliente-dark', nome: 'Marina Silva'),
          onTap: () {},
        ),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_permissionChannel, (call) async {
      if (call.method == 'requestPermissions') {
        return <int, int>{Permission.location.value: 0};
      }
      if (call.method == 'checkServiceStatus') {
        return 0;
      }
      if (call.method == 'shouldShowRequestPermissionRationale') {
        return false;
      }
      return 0;
    });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_permissionChannel, null);
  });

  testWidgets('clientes list shows premium search and section header',
      (tester) async {
    await pumpClientesList(tester);

    expect(find.text('Clientes'), findsOneWidget);
    expect(find.text('Base de clientes'), findsOneWidget);
    expect(find.byIcon(Icons.search), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(1));
  });

  testWidgets('clientes list shows offline guidance when fetch has no cache',
      (tester) async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(db.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          dbProvider.overrideWith((ref) => db),
          apiClientProvider.overrideWith((ref) => _offlineDio()),
          clienteReadUserIdProvider.overrideWith((ref) => () async => 'u9'),
        ],
        child: MaterialApp(
          theme: buildLightTheme(),
          home: const ClientesListScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Sem conexão para atualizar clientes'), findsOneWidget);
    expect(
      find.textContaining('Sem rede e sem cache disponível'),
      findsOneWidget,
    );
    expect(find.text('Tentar novamente'), findsOneWidget);
  });

  testWidgets('cliente detail groups hero and data into premium surfaces',
      (tester) async {
    await pumpClienteDetail(tester);
    final detailScroll = find.byType(Scrollable).first;

    expect(find.text('Resumo do cliente'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Histórico de OS'),
      300,
      scrollable: detailScroll,
    );
    await tester.pumpAndSettle();

    expect(find.text('Histórico de OS'), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(2));
  });

  testWidgets('novo cliente shows elevated step container', (tester) async {
    await pumpNovoCliente(tester);

    expect(find.text('Novo cliente'), findsOneWidget);
    expect(find.text('Cadastro guiado'), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(2));
    expect(find.text('GPS capturado'), findsWidgets);
  });

  testWidgets('cliente card uses theme-driven installer accent in dark mode',
      (tester) async {
    await pumpClienteCardDarkTheme(tester);

    final installerText = tester.widget<Text>(find.text('Técnico 1').last);

    expect(installerText.style?.color, buildDarkTheme().colorScheme.primary);
  });
}
