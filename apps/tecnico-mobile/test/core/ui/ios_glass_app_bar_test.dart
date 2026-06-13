import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/ios_glass_app_bar.dart';

void main() {
  testWidgets('mostra título, ação e tem vidro (BackdropFilter)',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          appBar: IosGlassAppBar(
            title: 'Novo cliente',
            actions: [
              IconButton(icon: const Icon(Icons.gps_fixed), onPressed: () {}),
            ],
          ),
          body: const SizedBox(),
        ),
      ),
    );
    expect(find.text('Novo cliente'), findsOneWidget);
    expect(find.byIcon(Icons.gps_fixed), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });
}
