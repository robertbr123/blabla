import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/branding/brand_tokens.dart';
import 'package:cliente_mobile/core/ui/capa_folha.dart';

void main() {
  testWidgets('CapaBackground renderiza filho sobre o gradiente', (t) async {
    await t.pumpWidget(const MaterialApp(
      home: CapaBackground(child: Text('capa')),
    ));
    expect(find.text('capa'), findsOneWidget);
  });

  testWidgets('FolhaContainer usa background claro no tema light', (t) async {
    await t.pumpWidget(MaterialApp(
      theme: ThemeData(brightness: Brightness.light),
      home: const FolhaContainer(child: Text('folha')),
    ));
    final box = t.widget<Container>(
      find.ancestor(of: find.text('folha'), matching: find.byType(Container)).first,
    );
    final deco = box.decoration as BoxDecoration;
    expect(deco.color, BrandTokens.background);
    expect(find.text('folha'), findsOneWidget);
  });

  testWidgets('FolhaContainer usa backgroundDark no tema dark', (t) async {
    await t.pumpWidget(MaterialApp(
      theme: ThemeData(brightness: Brightness.dark),
      home: const FolhaContainer(child: Text('folha')),
    ));
    final box = t.widget<Container>(
      find.ancestor(of: find.text('folha'), matching: find.byType(Container)).first,
    );
    final deco = box.decoration as BoxDecoration;
    expect(deco.color, BrandTokens.backgroundDark);
  });
}
