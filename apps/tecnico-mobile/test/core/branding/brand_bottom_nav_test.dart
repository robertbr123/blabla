import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_bottom_nav.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';

const _items = [
  BrandNavItem(
      icon: Icons.assignment_outlined,
      selectedIcon: Icons.assignment_rounded,
      label: 'OS'),
  BrandNavItem(
      icon: Icons.inventory_2_outlined,
      selectedIcon: Icons.inventory_2_rounded,
      label: 'Estoque'),
  BrandNavItem(
      icon: Icons.people_outline,
      selectedIcon: Icons.people_rounded,
      label: 'Clientes'),
  BrandNavItem(
      icon: Icons.person_outline,
      selectedIcon: Icons.person_rounded,
      label: 'Perfil'),
];

Future<void> _pump(
  WidgetTester tester, {
  required int selected,
  required void Function(int) onSelect,
  Brightness brightness = Brightness.light,
}) {
  return tester.pumpWidget(
    MaterialApp(
      theme: buildBrandTheme(brightness),
      home: Scaffold(
        bottomNavigationBar: BrandBottomNav(
          selectedIndex: selected,
          onSelect: onSelect,
          items: _items,
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('renderiza um slot com label por item', (tester) async {
    await _pump(tester, selected: 0, onSelect: (_) {});
    for (final it in _items) {
      expect(find.text(it.label), findsOneWidget);
    }
  });

  testWidgets('tocar em aba não-selecionada chama onSelect com o índice',
      (tester) async {
    int? picked;
    await _pump(tester, selected: 0, onSelect: (i) => picked = i);
    await tester.tap(find.text('Clientes'));
    await tester.pump();
    expect(picked, 2);
  });

  testWidgets('tocar na aba já selecionada não chama onSelect',
      (tester) async {
    var calls = 0;
    await _pump(tester, selected: 0, onSelect: (_) => calls++);
    await tester.tap(find.text('OS'));
    await tester.pump();
    expect(calls, 0);
  });

  testWidgets('aba selecionada expõe Semantics selected=true', (tester) async {
    await _pump(tester, selected: 2, onSelect: (_) {});
    final handle = tester.ensureSemantics();
    expect(
      tester.getSemantics(find.text('Clientes')),
      matchesSemantics(label: 'Clientes', isSelected: true, isButton: true),
    );
    handle.dispose();
  });

  testWidgets('aplica vidro com BackdropFilter', (tester) async {
    await _pump(tester, selected: 0, onSelect: (_) {});
    expect(find.byType(BackdropFilter), findsOneWidget);
  });

  testWidgets('a lente desliza ao trocar de aba (muda o left)',
      (tester) async {
    await _pump(tester, selected: 0, onSelect: (_) {});
    final left0 = tester
        .widget<AnimatedPositioned>(find.byType(AnimatedPositioned))
        .left;
    await _pump(tester, selected: 2, onSelect: (_) {});
    await tester.pumpAndSettle();
    final left2 = tester
        .widget<AnimatedPositioned>(find.byType(AnimatedPositioned))
        .left;
    expect(find.byType(AnimatedPositioned), findsOneWidget);
    expect(left0, isNotNull);
    expect(left2, greaterThan(left0!));
  });

  testWidgets('vidro presente também no tema escuro', (tester) async {
    await _pump(tester,
        selected: 0, onSelect: (_) {}, brightness: Brightness.dark);
    expect(find.byType(BackdropFilter), findsOneWidget);
    expect(find.text('OS'), findsOneWidget);
  });
}
