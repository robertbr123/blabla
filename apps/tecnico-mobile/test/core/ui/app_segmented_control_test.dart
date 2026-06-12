import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/app_segmented_control.dart';

void main() {
  const segs = [
    AppSegment(value: 0, label: 'Todas'),
    AppSegment(value: 1, label: 'Em andamento'),
    AppSegment(value: 2, label: 'Concluídas'),
  ];

  testWidgets('renderiza labels e dispara onChanged ao tocar', (tester) async {
    int? picked;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: AppSegmentedControl<int>(
            segments: segs,
            selected: 0,
            onChanged: (v) => picked = v,
          ),
        ),
      ),
    );
    for (final s in segs) {
      expect(find.text(s.label), findsOneWidget);
    }
    await tester.tap(find.text('Concluídas'));
    await tester.pump();
    expect(picked, 2);
  });

  testWidgets('tocar no já selecionado não dispara onChanged', (tester) async {
    var calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: AppSegmentedControl<int>(
            segments: segs,
            selected: 0,
            onChanged: (_) => calls++,
          ),
        ),
      ),
    );
    await tester.tap(find.text('Todas'));
    await tester.pump();
    expect(calls, 0);
  });
}
