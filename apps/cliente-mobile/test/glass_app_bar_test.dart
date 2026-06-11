import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/glass_app_bar.dart';

void main() {
  testWidgets('GlassAppBar renderiza titulo e aplica BackdropFilter',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          extendBodyBehindAppBar: true,
          appBar: GlassAppBar(title: 'Minha Tela'),
          body: SizedBox.expand(),
        ),
      ),
    );
    expect(find.text('Minha Tela'), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });

  testWidgets('GlassAppBar aceita actions', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          appBar: GlassAppBar(
            title: 'Tela',
            actions: [IconButton(icon: const Icon(Icons.add), onPressed: () {})],
          ),
          body: const SizedBox.expand(),
        ),
      ),
    );
    expect(find.byIcon(Icons.add), findsOneWidget);
  });
}
