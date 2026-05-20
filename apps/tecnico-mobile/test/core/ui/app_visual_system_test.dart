import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_section_header.dart';
import 'package:tecnico_mobile/core/ui/app_status_chip.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';

void main() {
  testWidgets('premium theme exposes command-center palette', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(body: SizedBox()),
      ),
    );

    final context = tester.element(find.byType(SizedBox));
    final scheme = Theme.of(context).colorScheme;

    expect(scheme.primary.value, const Color(0xFF17324D).value);
    expect(scheme.surfaceContainerLowest.value, const Color(0xFFF6F1E8).value);
  });

  testWidgets('status chip renders label and info accent', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(
          body: AppStatusChip(label: 'Em andamento', tone: AppStatusTone.info),
        ),
      ),
    );

    final label = tester.widget<Text>(find.text('Em andamento'));

    expect(find.text('Em andamento'), findsOneWidget);
    expect(label.style?.color?.value, const Color(0xFF17324D).value);
  });

  testWidgets('surface card keeps rounded premium container', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildLightTheme(),
        home: const Scaffold(
          body: AppSurfaceCard(child: Text('Conteudo')),
        ),
      ),
    );

    final container = tester.widget<Container>(find.byType(Container).first);
    final decoration = container.decoration! as BoxDecoration;

    expect(find.text('Conteudo'), findsOneWidget);
    expect(
      decoration.borderRadius,
      BorderRadius.circular(24),
    );
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
