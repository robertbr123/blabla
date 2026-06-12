import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';

void main() {
  test('tema claro usa fundo agrupado iOS (#F2F2F7) com card branco', () {
    final scheme = buildBrandTheme(Brightness.light).colorScheme;
    expect(scheme.surface, const Color(0xFFF2F2F7));
    expect(scheme.surfaceContainer, const Color(0xFFFFFFFF));
  });

  test('tema escuro aprofunda o fundo agrupado', () {
    final scheme = buildBrandTheme(Brightness.dark).colorScheme;
    expect(scheme.surface, const Color(0xFF0B1120));
  });

  test('cardTheme usa raio 20 sem borda dura', () {
    final card = buildBrandTheme(Brightness.light).cardTheme;
    final shape = card.shape! as RoundedRectangleBorder;
    expect(shape.borderRadius, BorderRadius.circular(20));
    expect(shape.side, BorderSide.none);
  });

  test('iosLargeTitle tem tamanho e peso de large title', () {
    final scheme = buildBrandTheme(Brightness.light).colorScheme;
    final style = iosLargeTitle(scheme);
    expect(style.fontSize, 30);
    expect(style.fontWeight, FontWeight.w800);
    expect(style.letterSpacing, -0.5);
    expect(style.height, 1.1);
    expect(style.color, scheme.onSurface);
  });

  testWidgets('AppSurfaceCard é card grouped (raio 20 + sombra) com clip',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: const Scaffold(body: AppSurfaceCard(child: Text('x'))),
      ),
    );

    expect(find.text('x'), findsOneWidget);

    final decorated = tester.widget<DecoratedBox>(
      find
          .descendant(
            of: find.byType(AppSurfaceCard),
            matching: find.byType(DecoratedBox),
          )
          .first,
    );
    final decoration = decorated.decoration as BoxDecoration;
    expect(decoration.borderRadius, BorderRadius.circular(20));
    expect(decoration.boxShadow, isNotEmpty);

    expect(
      find.descendant(
        of: find.byType(AppSurfaceCard),
        matching: find.byType(ClipRRect),
      ),
      findsOneWidget,
    );
  });
}
