import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:tecnico_mobile/core/sync/sync_service.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/features/os/os_data.dart';
import 'package:tecnico_mobile/features/os/os_list_screen.dart';
import 'package:tecnico_mobile/features/os/widgets/home_filter_strip.dart';
import 'package:tecnico_mobile/features/shell/main_shell.dart';

Map<String, dynamic> _row({
  required String id,
  required String codigo,
  required String status,
  required String cliente,
  DateTime? agendamentoAt,
  DateTime? criadaEm,
}) {
  return {
    'id': id,
    'codigo': codigo,
    'status': status,
    'problema': 'Sem sinal no modem',
    'endereco': 'Rua A, 100',
    'nome_cliente': cliente,
    'agendamento_at': agendamentoAt?.toUtc().toIso8601String(),
    'criada_em': (criadaEm ?? DateTime.now()).toUtc().toIso8601String(),
  };
}

List<Map<String, dynamic>> _defaultRows() {
  final now = DateTime.now();
  return [
    _row(
      id: 'os-1',
      codigo: 'OS-001',
      status: 'pendente',
      cliente: 'Cliente A',
      agendamentoAt: now.add(const Duration(hours: 2)),
      criadaEm: now.subtract(const Duration(hours: 3)),
    ),
    _row(
      id: 'os-2',
      codigo: 'OS-002',
      status: 'em_andamento',
      cliente: 'Cliente B',
      agendamentoAt: now.add(const Duration(hours: 5)),
      criadaEm: now.subtract(const Duration(hours: 5)),
    ),
    _row(
      id: 'os-3',
      codigo: 'OS-003',
      status: 'concluida',
      cliente: 'Cliente C',
      criadaEm: now.subtract(const Duration(days: 1)),
    ),
  ];
}

Future<void> _pumpHome(
  WidgetTester tester, {
  Widget? child,
  int pendingCount = 2,
  List<Map<String, dynamic>>? rows,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        osListStreamProvider.overrideWith(
          (ref) => Stream.value(rows ?? _defaultRows()),
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
    final mainScroll = find
        .descendant(
          of: find.byKey(const ValueKey('os-home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;

    expect(find.text('Home'), findsOneWidget);
    expect(find.textContaining('Hoje'), findsOneWidget);
    expect(find.text('Pendentes'), findsWidgets);
    expect(find.textContaining('aguardando upload'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('OS-001'),
      300,
      scrollable: mainScroll,
    );

    expect(find.text('OS-001'), findsOneWidget);
    expect(find.text('OS-002'), findsNothing);
  });

  testWidgets('home shows premium empty state when selected queue is empty',
      (tester) async {
    final now = DateTime.now();

    await _pumpHome(
      tester,
      rows: [
        _row(
          id: 'os-3',
          codigo: 'OS-003',
          status: 'concluida',
          cliente: 'Cliente C',
          criadaEm: now.subtract(const Duration(days: 1)),
        ),
      ],
      pendingCount: 0,
    );

    final mainScroll = find
        .descendant(
          of: find.byKey(const ValueKey('os-home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;

    await tester.scrollUntilVisible(
      find.text('Tudo em dia por aqui'),
      250,
      scrollable: mainScroll,
    );

    expect(find.text('Tudo em dia por aqui'), findsOneWidget);
    expect(
      find.textContaining('Nenhuma OS pendente precisa da sua atenção agora'),
      findsOneWidget,
    );
    expect(find.text('Atualizar'), findsOneWidget);
  });

  testWidgets(
      'home hero uses the next future schedule when overdue items exist',
      (tester) async {
    final now = DateTime.now();
    final overdue = now.subtract(const Duration(hours: 1));
    final upcoming = now.add(const Duration(hours: 3));

    await _pumpHome(
      tester,
      rows: [
        _row(
          id: 'os-overdue',
          codigo: 'OS-100',
          status: 'pendente',
          cliente: 'Cliente Overdue',
          agendamentoAt: overdue,
        ),
        _row(
          id: 'os-next',
          codigo: 'OS-101',
          status: 'pendente',
          cliente: 'Cliente Next',
          agendamentoAt: upcoming,
        ),
      ],
    );

    expect(
      find.text('Próxima visita ${DateFormat('HH:mm').format(upcoming)}'),
      findsOneWidget,
    );
    expect(
      find.text('Próxima visita ${DateFormat('HH:mm').format(overdue)}'),
      findsNothing,
    );
  });

  testWidgets('home filters can switch between all os and em andamento',
      (tester) async {
    await _pumpHome(tester);
    final mainScroll = find
        .descendant(
          of: find.byKey(const ValueKey('os-home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('home-filter-todas')),
      300,
      scrollable: mainScroll,
    );
    await tester.tap(find.byKey(const ValueKey('home-filter-todas')));
    await tester.pumpAndSettle();

    expect(find.text('OS-001'), findsOneWidget);
    expect(find.text('OS-002'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('OS-003'),
      220,
      scrollable: mainScroll,
    );
    expect(find.text('OS-003'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('home-filter-andamento')),
      150,
      scrollable: mainScroll,
    );
    final horizontalFilterScroll = find.descendant(
      of: find.byType(HomeFilterStrip),
      matching: find.byType(Scrollable),
    );
    await tester.drag(
      horizontalFilterScroll,
      const Offset(-220, 0),
      warnIfMissed: false,
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.descendant(
        of: find.byKey(const ValueKey('home-filter-andamento')),
        matching: find.byType(InkWell),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('OS-001'), findsNothing);
    expect(find.text('OS-002'), findsOneWidget);
    expect(find.text('OS-003'), findsNothing);
  });

  testWidgets('selected home controls expose semantics state', (tester) async {
    final handle = tester.ensureSemantics();

    await _pumpHome(tester);
    await tester.pumpAndSettle();

    final summarySemantics = tester.widget<Semantics>(
      find.byKey(const ValueKey('home-summary-semantics-Pendentes')),
    );

    expect(
      summarySemantics.properties.button,
      isTrue,
    );
    expect(summarySemantics.properties.selected, isTrue);
    expect(
      summarySemantics.properties.label,
      'Resumo Pendentes, 1, Aguardando visita',
    );

    final mainScroll = find
        .descendant(
          of: find.byKey(const ValueKey('os-home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('home-filter-pendente')),
      300,
      scrollable: mainScroll,
    );

    var filterSemantics = tester.widget<Semantics>(
      find.byKey(const ValueKey('home-filter-pendente')),
    );
    expect(filterSemantics.properties.button, isTrue);
    expect(filterSemantics.properties.selected, isTrue);
    expect(filterSemantics.properties.label, 'Filtro Pendentes');

    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('home-filter-todas')),
      300,
      scrollable: mainScroll,
    );
    await tester.tap(find.byKey(const ValueKey('home-filter-todas')));
    await tester.pumpAndSettle();

    filterSemantics = tester.widget<Semantics>(
      find.byKey(const ValueKey('home-filter-todas')),
    );
    expect(filterSemantics.properties.selected, isTrue);
    handle.dispose();
  });

  testWidgets('home list keeps lazy rendering for longer os queues',
      (tester) async {
    final now = DateTime.now();
    final rows = List<Map<String, dynamic>>.generate(30, (index) {
      return _row(
        id: 'os-$index',
        codigo: 'OS-${index.toString().padLeft(3, '0')}',
        status: 'pendente',
        cliente: 'Cliente $index',
        agendamentoAt: now.add(Duration(minutes: index + 1)),
        criadaEm: now.subtract(Duration(minutes: index)),
      );
    });

    await _pumpHome(tester, rows: rows);
    final mainScroll = find
        .descendant(
          of: find.byKey(const ValueKey('os-home-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;

    expect(find.text('OS-029'), findsNothing);
    await tester.scrollUntilVisible(
      find.text('OS-029'),
      400,
      scrollable: mainScroll,
    );
    expect(find.text('OS-029'), findsOneWidget);
  });

  testWidgets('main shell exposes home as the first destination',
      (tester) async {
    await _pumpHome(tester, child: const MainShell());

    expect(
      find.descendant(
        of: find.byType(NavigationBar),
        matching: find.text('Home'),
      ),
      findsOneWidget,
    );
  });
}
