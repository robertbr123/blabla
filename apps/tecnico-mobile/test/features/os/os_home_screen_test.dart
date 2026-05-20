import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/features/os/os_data.dart';
import 'package:tecnico_mobile/features/os/os_list_screen.dart';
import 'package:tecnico_mobile/features/shell/main_shell.dart';

const _rows = [
  {
    'id': 'os-1',
    'codigo': 'OS-001',
    'status': 'pendente',
    'problema': 'Sem sinal no modem',
    'endereco': 'Rua A, 100',
    'nome_cliente': 'Cliente A',
    'agendamento_at': '2026-05-20T12:00:00Z',
    'criada_em': '2026-05-19T11:00:00Z',
  },
  {
    'id': 'os-2',
    'codigo': 'OS-002',
    'status': 'em_andamento',
    'problema': 'Troca de roteador',
    'endereco': 'Rua B, 200',
    'nome_cliente': 'Cliente B',
    'agendamento_at': '2026-05-20T15:30:00Z',
    'criada_em': '2026-05-19T10:00:00Z',
  },
  {
    'id': 'os-3',
    'codigo': 'OS-003',
    'status': 'concluida',
    'problema': 'Configurar repetidor',
    'endereco': 'Rua C, 300',
    'nome_cliente': 'Cliente C',
    'agendamento_at': null,
    'criada_em': '2026-05-18T09:00:00Z',
  },
];

Future<void> _pumpHome(
  WidgetTester tester, {
  Widget? child,
  int pendingCount = 2,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        osListStreamProvider.overrideWith(
          (ref) => Stream.value(_rows),
        ),
        pendingCountProvider.overrideWith(
          (ref) => Stream<int>.value(pendingCount),
        ),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: child ?? const OsListScreen(),
      ),
    ),
  );

  await tester.pump();
}

void main() {
  testWidgets('home screen shows operational hero and dominant os list',
      (tester) async {
    await _pumpHome(tester);

    expect(find.text('Home'), findsOneWidget);
    expect(find.textContaining('Hoje'), findsOneWidget);
    expect(find.text('Pendentes'), findsWidgets);
    expect(find.text('OS-001'), findsOneWidget);
    expect(find.text('OS-002'), findsNothing);
    expect(find.textContaining('aguardando upload'), findsOneWidget);
  });

  testWidgets('home filters can switch between all os and em andamento',
      (tester) async {
    await _pumpHome(tester);

    await tester.tap(find.text('Todas').last);
    await tester.pumpAndSettle();

    expect(find.text('OS-001'), findsOneWidget);
    expect(find.text('OS-002'), findsOneWidget);
    expect(find.text('OS-003'), findsOneWidget);

    await tester.tap(find.text('Em andamento').last);
    await tester.pumpAndSettle();

    expect(find.text('OS-001'), findsNothing);
    expect(find.text('OS-002'), findsOneWidget);
    expect(find.text('OS-003'), findsNothing);
  });

  testWidgets('main shell exposes home as the first destination',
      (tester) async {
    await _pumpHome(tester, child: const MainShell());

    expect(find.byIcon(Icons.home_rounded), findsOneWidget);
    expect(find.text('Home'), findsAtLeastNWidgets(1));
  });
}
