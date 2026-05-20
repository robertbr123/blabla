import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';
import 'package:tecnico_mobile/features/perfil/perfil_data.dart';
import 'package:tecnico_mobile/features/perfil/perfil_screen.dart';

Perfil _perfil() {
  return Perfil(
    userId: 'user-1',
    email: 'tecnico@example.com',
    nome: 'Marina Silva',
    whatsapp: '92999998888',
    role: 'Técnica de campo',
    fotoB64: null,
    ativo: true,
    lastGpsTs: '2026-05-20T09:30:00Z',
    estatisticas: PerfilEstatisticas(
      osPendentes: 3,
      osEmAndamento: 1,
      osConcluidasMes: 18,
      csatAvgMes: 4.8,
    ),
  );
}

Future<void> pumpPerfil(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        perfilProvider.overrideWith((ref) async => _perfil()),
      ],
      child: MaterialApp(
        theme: buildLightTheme(),
        home: const PerfilScreen(),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

void main() {
  testWidgets('perfil groups account actions in premium sections',
      (tester) async {
    await pumpPerfil(tester);
    final profileScroll = find.byType(Scrollable).first;

    await tester.scrollUntilVisible(
      find.text('Conta'),
      250,
      scrollable: profileScroll,
    );
    await tester.pumpAndSettle();

    expect(find.text('Conta'), findsOneWidget);
    expect(find.text('Sobre'), findsOneWidget);
    expect(find.text('Sua atividade recente'), findsOneWidget);
    expect(find.byType(AppSurfaceCard), findsAtLeastNWidgets(3));
  });
}
