import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/pressable_scale.dart';

void main() {
  testWidgets('PressableScale chama onTap e renderiza child', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: PressableScale(
          onTap: () => tapped = true,
          child: const Text('card'),
        ),
      ),
    );
    expect(find.text('card'), findsOneWidget);
    await tester.tap(find.text('card'));
    await tester.pumpAndSettle();
    expect(tapped, isTrue);
  });

  testWidgets('PressableScale com onTap null nao explode ao tocar', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PressableScale(
          onTap: null,
          child: Text('sem-tap'),
        ),
      ),
    );
    expect(find.text('sem-tap'), findsOneWidget);
    await tester.tap(find.text('sem-tap'));
    await tester.pumpAndSettle();
    // Nenhuma exception deve ter sido lancada
  });

  testWidgets('PressableScale anima escala 0.97 ao pressionar e volta a 1.0', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PressableScale(
          onTap: null,
          child: SizedBox(width: 100, height: 100, child: Text('target')),
        ),
      ),
    );

    // Inicia o gesto (pressionar, sem soltar)
    final gesture = await tester.startGesture(tester.getCenter(find.text('target')));
    await tester.pump(const Duration(milliseconds: 50));

    final scalePressionado = tester.widget<AnimatedScale>(find.byType(AnimatedScale)).scale;
    expect(scalePressionado, closeTo(0.97, 0.001));

    // Solta o gesto
    await gesture.up();
    await tester.pumpAndSettle();

    final scaleSolto = tester.widget<AnimatedScale>(find.byType(AnimatedScale)).scale;
    expect(scaleSolto, closeTo(1.0, 0.001));
  });
}

