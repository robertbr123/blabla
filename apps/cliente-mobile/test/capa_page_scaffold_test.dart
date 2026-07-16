import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/capa_page_scaffold.dart';

void main() {
  testWidgets('renderiza titulo, child e botao voltar quando pode pop',
      (t) async {
    await t.pumpWidget(MaterialApp(
      home: const Placeholder(),
    ));
    // Empurra uma rota pra Navigator.canPop ser true.
    final nav = t.state<NavigatorState>(find.byType(Navigator));
    nav.push(MaterialPageRoute(
      builder: (_) => const CapaPageScaffold(
        title: 'Minha tela',
        child: Text('conteudo'),
      ),
    ));
    await t.pumpAndSettle();
    expect(find.text('Minha tela'), findsOneWidget);
    expect(find.text('conteudo'), findsOneWidget);
    expect(find.byIcon(Icons.arrow_back_rounded), findsOneWidget);
  });

  testWidgets('sem botao voltar quando nao pode pop', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: CapaPageScaffold(title: 'Raiz', child: Text('x')),
    ));
    expect(find.byIcon(Icons.arrow_back_rounded), findsNothing);
  });
}
