import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/branding/brand_theme.dart';
import 'package:tecnico_mobile/core/ui/ios_glass_header.dart';

void main() {
  testWidgets('mostra título, ação e tem vidro (BackdropFilter)',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBrandTheme(Brightness.light),
        home: Scaffold(
          body: CustomScrollView(
            slivers: [
              IosGlassHeader(
                title: 'Ordens de Serviço',
                subtitle: '3 ordens em foco',
                actions: [
                  IconButton(icon: const Icon(Icons.refresh), onPressed: () {}),
                ],
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 1200)),
            ],
          ),
        ),
      ),
    );
    expect(find.text('Ordens de Serviço'), findsOneWidget);
    expect(find.text('3 ordens em foco'), findsOneWidget);
    expect(find.byIcon(Icons.refresh), findsOneWidget);
    expect(find.byType(BackdropFilter), findsOneWidget);
  });
}
