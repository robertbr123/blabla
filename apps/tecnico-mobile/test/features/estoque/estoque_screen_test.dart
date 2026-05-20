import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'dart:async';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';
import 'package:tecnico_mobile/features/estoque/estoque_data.dart';
import 'package:tecnico_mobile/features/estoque/estoque_screen.dart';

Future<void> pumpEstoque(
  WidgetTester tester, {
  List<EstoqueLinha>? linhas,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        estoqueSaldoProvider.overrideWith(
          (ref) async =>
              linhas ??
              [
                EstoqueLinha(
                  itemId: 'item-1',
                  sku: 'ONU-01',
                  nome: 'ONU Wi-Fi 6',
                  categoria: 'ONU',
                  serializado: true,
                  saldo: 3,
                ),
                EstoqueLinha(
                  itemId: 'item-2',
                  sku: 'CABO-10',
                  nome: 'Cabo drop 100m',
                  categoria: 'Cabos',
                  serializado: false,
                  saldo: 8,
                ),
              ],
        ),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: const EstoqueScreen(),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

void main() {
  testWidgets('estoque shows premium loading state while saldo is pending',
      (tester) async {
    final completer = Completer<List<EstoqueLinha>>();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          estoqueSaldoProvider.overrideWith((ref) => completer.future),
        ],
        child: MaterialApp(
          theme: buildLightTheme(),
          home: const EstoqueScreen(),
        ),
      ),
    );

    await tester.pump();

    expect(find.text('Carregando estoque'), findsOneWidget);
    expect(
      find.text('Conferindo saldo e categorias para sua próxima visita.'),
      findsOneWidget,
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('estoque shows summary surface and premium filters',
      (tester) async {
    await pumpEstoque(tester);

    expect(find.text('Visão do estoque'), findsOneWidget);
    expect(find.textContaining('Itens em estoque'), findsOneWidget);
    expect(find.textContaining('Categorias'), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(2));
  });

  testWidgets(
      'estoque empty state explains there are no stock items when dataset is empty',
      (tester) async {
    await pumpEstoque(tester, linhas: const []);

    expect(find.text('Nenhum item encontrado.'), findsOneWidget);
    expect(
      find.textContaining('Nenhum item de estoque foi disponibilizado'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Ajuste a busca ou desative o filtro'),
      findsNothing,
    );
  });

  testWidgets(
      'estoque empty state suggests refining filters when search removes all results',
      (tester) async {
    await pumpEstoque(tester);

    await tester.enterText(
      find.byType(TextField),
      'material-inexistente',
    );
    await tester.pumpAndSettle();

    expect(find.text('Nenhum item encontrado.'), findsOneWidget);
    expect(
      find.textContaining('Ajuste a busca ou desative o filtro'),
      findsOneWidget,
    );
  });
}
