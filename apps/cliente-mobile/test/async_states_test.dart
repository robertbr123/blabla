import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/async_states.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets('ErrorCard mostra mensagem e chama onRetry', (tester) async {
    var retried = false;
    await tester.pumpWidget(wrap(
      ErrorCard(
        message: 'Não conseguimos carregar agora.',
        onRetry: () => retried = true,
      ),
    ));
    expect(find.text('Não conseguimos carregar agora.'), findsOneWidget);
    await tester.tap(find.text('Tentar de novo'));
    expect(retried, isTrue);
  });

  testWidgets('EmptyState mostra icone, titulo e subtitulo', (tester) async {
    await tester.pumpWidget(wrap(
      const EmptyState(
        icon: Icons.inbox_rounded,
        title: 'Nada por aqui',
        subtitle: 'Quando algo chegar, aparece nesta tela.',
      ),
    ));
    expect(find.byIcon(Icons.inbox_rounded), findsOneWidget);
    expect(find.text('Nada por aqui'), findsOneWidget);
    expect(find.text('Quando algo chegar, aparece nesta tela.'), findsOneWidget);
  });

  testWidgets('ErrorCard sem onRetry não mostra botão', (tester) async {
    await tester.pumpWidget(wrap(const ErrorCard()));
    expect(find.text('Tentar de novo'), findsNothing);
  });

  testWidgets('EmptyState sem subtitulo', (tester) async {
    await tester.pumpWidget(wrap(
      const EmptyState(icon: Icons.inbox_rounded, title: 'Nada por aqui'),
    ));
    expect(find.text('Nada por aqui'), findsOneWidget);
  });

  testWidgets('AsyncBuilder renderiza data/loading/error', (tester) async {
    // data
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: const AsyncValue.data('oi'),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.text('oi'), findsOneWidget);

    // loading (default = spinner centralizado)
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: const AsyncValue.loading(),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // error (default = ErrorCard)
    await tester.pumpWidget(wrap(
      AsyncBuilder<String>(
        value: AsyncValue<String>.error('boom', StackTrace.empty),
        builder: (data) => Text(data),
      ),
    ));
    expect(find.byType(ErrorCard), findsOneWidget);
  });
}
