import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_state_panel.dart';

void main() {
  Future<void> pumpPanel(
    WidgetTester tester,
    Widget child,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: Scaffold(body: child),
      ),
    );
  }

  testWidgets('state panel renders loading variant with progress and message',
      (tester) async {
    await pumpPanel(
      tester,
      const AppStatePanel.loading(
        title: 'Carregando estoque',
        message: 'Conferindo saldo e categorias para sua próxima visita.',
      ),
    );

    expect(find.text('Carregando estoque'), findsOneWidget);
    expect(
      find.text('Conferindo saldo e categorias para sua próxima visita.'),
      findsOneWidget,
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('state panel renders offline action with premium copy',
      (tester) async {
    await pumpPanel(
      tester,
      AppStatePanel.offline(
        title: 'Sem conexão para atualizar clientes',
        message:
            'Sem rede e sem cache disponível para essa lista. Tente novamente quando o sinal voltar.',
        actionLabel: 'Tentar novamente',
        onAction: () {},
      ),
    );

    expect(find.text('Sem conexão para atualizar clientes'), findsOneWidget);
    expect(
      find.textContaining('Sem rede e sem cache disponível'),
      findsOneWidget,
    );
    expect(find.text('Tentar novamente'), findsOneWidget);
    expect(find.byIcon(Icons.wifi_off_rounded), findsOneWidget);
  });
}
