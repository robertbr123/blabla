import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';
import 'package:tecnico_mobile/features/estoque/estoque_data.dart';
import 'package:tecnico_mobile/features/estoque/estoque_screen.dart';

Future<void> pumpEstoque(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        estoqueSaldoProvider.overrideWith(
          (ref) async => [
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
  testWidgets('estoque shows summary surface and premium filters',
      (tester) async {
    await pumpEstoque(tester);

    expect(find.text('Visão do estoque'), findsOneWidget);
    expect(find.textContaining('Itens em estoque'), findsOneWidget);
    expect(find.textContaining('Categorias'), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(2));
  });
}
