import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_section_header.dart';
import 'package:tecnico_mobile/core/ui/app_status_chip.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';

void main() {
  test('legacy brand aliases preserve their original meanings', () {
    expect(brandGreen.value, const Color(0xFF16A34A).value);
    expect(brandGreenLight.value, const Color(0xFF22C55E).value);
    expect(brandInk.value, const Color(0xFF0E1729).value);
    expect(brandCream.value, const Color(0xFFF8F5EE).value);
    expect(brandBlue.value, const Color(0xFF16A34A).value);
    expect(brandCyan.value, const Color(0xFF22C55E).value);
    expect(brandBlueDark.value, const Color(0xFF4ADE80).value);
    expect(brandCyanDark.value, const Color(0xFF34D399).value);
  });

  testWidgets('premium theme exposes command-center palette', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(body: SizedBox()),
      ),
    );

    final context = tester.element(find.byType(SizedBox));
    final theme = Theme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final cardTheme = theme.cardTheme;

    expect(scheme.primary.value, const Color(0xFF17324D).value);
    expect(scheme.surfaceContainerLowest.value, const Color(0xFFF6F1E8).value);
    expect((cardTheme.shape! as RoundedRectangleBorder).borderRadius,
        BorderRadius.circular(24));
  });

  testWidgets('status chip derives tone colors from the active theme',
      (tester) async {
    Future<void> expectChipColors({
      required ThemeData theme,
      required String label,
      required AppStatusTone tone,
      required Color expectedColor,
    }) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Theme(
            data: theme,
            child: Scaffold(
              body: AppStatusChip(label: label, tone: tone),
            ),
          ),
        ),
      );

      final chipLabel = tester.widget<Text>(find.text(label));
      final chipContainer = tester.widget<Container>(
        find.ancestor(of: find.text(label), matching: find.byType(Container)),
      );
      final decoration = chipContainer.decoration! as BoxDecoration;
      final border = decoration.border! as Border;

      expect(chipLabel.style?.color?.value, expectedColor.value);
      expect(
          decoration.color?.value, expectedColor.withValues(alpha: 0.10).value);
      expect(
          border.top.color.value, expectedColor.withValues(alpha: 0.18).value);
    }

    final lightTheme = buildLightTheme();
    final darkTheme = buildDarkTheme();

    await expectChipColors(
      theme: lightTheme,
      label: 'Info',
      tone: AppStatusTone.info,
      expectedColor: lightTheme.colorScheme.primary,
    );
    await expectChipColors(
      theme: lightTheme,
      label: 'Sucesso',
      tone: AppStatusTone.success,
      expectedColor: lightTheme.colorScheme.tertiary,
    );
    await expectChipColors(
      theme: lightTheme,
      label: 'Alerta',
      tone: AppStatusTone.warning,
      expectedColor: lightTheme.colorScheme.secondary,
    );
    await expectChipColors(
      theme: lightTheme,
      label: 'Erro',
      tone: AppStatusTone.danger,
      expectedColor: lightTheme.colorScheme.error,
    );
    await expectChipColors(
      theme: lightTheme,
      label: 'Neutro',
      tone: AppStatusTone.neutral,
      expectedColor: lightTheme.colorScheme.onSurfaceVariant,
    );
    await expectChipColors(
      theme: darkTheme,
      label: 'Sucesso escuro',
      tone: AppStatusTone.success,
      expectedColor: darkTheme.colorScheme.tertiary,
    );
    await expectChipColors(
      theme: darkTheme,
      label: 'Alerta escuro',
      tone: AppStatusTone.warning,
      expectedColor: darkTheme.colorScheme.secondary,
    );
  });

  testWidgets('surface card reuses the shared card theme', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(
          body: AppSurfaceCard(child: Text('Conteudo')),
        ),
      ),
    );

    final card = tester.widget<Card>(find.byType(Card));
    final paddingFinder = find.descendant(
      of: find.byType(Card),
      matching: find.byWidgetPredicate(
        (widget) =>
            widget is Padding && widget.padding == const EdgeInsets.all(16),
      ),
    );

    expect(find.text('Conteudo'), findsOneWidget);
    expect(find.byType(Card), findsOneWidget);
    expect(card.color, isNull);
    expect(card.shape, isNull);
    expect(card.shadowColor, isNull);
    expect(paddingFinder, findsOneWidget);
  });

  testWidgets('section header shows title and action label', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: Scaffold(
          body: AppSectionHeader(
            title: 'Hoje',
            actionLabel: 'Ver tudo',
            onAction: () {},
          ),
        ),
      ),
    );

    expect(find.text('Hoje'), findsOneWidget);
    expect(find.text('Ver tudo'), findsOneWidget);
  });
}
