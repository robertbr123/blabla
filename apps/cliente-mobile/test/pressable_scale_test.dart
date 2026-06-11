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
}
