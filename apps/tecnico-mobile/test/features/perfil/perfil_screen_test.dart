import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/theme.dart';
import 'package:tecnico_mobile/core/ui/app_surfaces.dart';
import 'package:tecnico_mobile/features/perfil/perfil_data.dart';
import 'package:tecnico_mobile/features/perfil/perfil_screen.dart';

const _validPhotoB64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9VEWilQAAAAASUVORK5CYII=';

class _FakePerfilActions extends PerfilActions {
  _FakePerfilActions() : super(Dio());

  int removerFotoCalls = 0;

  @override
  Future<void> removerFoto() async {
    removerFotoCalls++;
  }
}

Perfil _perfil({
  String? lastGpsTs,
  String? fotoB64,
}) {
  return Perfil(
    userId: 'user-1',
    email: 'tecnico@example.com',
    nome: 'Marina Silva',
    whatsapp: '92999998888',
    role: 'Técnica de campo',
    fotoB64: fotoB64,
    ativo: true,
    lastGpsTs: lastGpsTs ?? DateTime.now().toUtc().toIso8601String(),
    estatisticas: PerfilEstatisticas(
      osPendentes: 3,
      osEmAndamento: 1,
      osConcluidasMes: 18,
      csatAvgMes: 4.8,
    ),
  );
}

Future<void> pumpPerfil(
  WidgetTester tester, {
  Perfil? perfil,
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        perfilProvider.overrideWith((ref) async => perfil ?? _perfil()),
        ...overrides,
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
  test('perfil considers gps snapshot recent only within freshness window', () {
    final now = DateTime(2026, 5, 20, 12);

    final recent = _perfil(
      lastGpsTs:
          now.subtract(const Duration(hours: 2)).toUtc().toIso8601String(),
    );
    final stale = _perfil(
      lastGpsTs:
          now.subtract(const Duration(days: 2)).toUtc().toIso8601String(),
    );
    final invalid = _perfil(lastGpsTs: 'not-a-date');

    expect(recent.hasRecentGpsSnapshot(now: now), isTrue);
    expect(stale.hasRecentGpsSnapshot(now: now), isFalse);
    expect(invalid.hasRecentGpsSnapshot(now: now), isFalse);
  });

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

  testWidgets('closing photo sheet without an action does not remove the photo',
      (tester) async {
    final fakeActions = _FakePerfilActions();

    await pumpPerfil(
      tester,
      perfil: _perfil(fotoB64: _validPhotoB64),
      overrides: [
        perfilActionsProvider.overrideWith((ref) => fakeActions),
      ],
    );

    await tester.tap(find.byIcon(Icons.camera_alt));
    await tester.pumpAndSettle();

    expect(find.text('Remover foto atual'), findsOneWidget);

    Navigator.of(tester.element(find.text('Remover foto atual'))).pop();
    await tester.pumpAndSettle();

    expect(fakeActions.removerFotoCalls, 0);
    expect(find.text('Foto removida.'), findsNothing);
  });

  testWidgets('explicit photo removal uses the delete action only',
      (tester) async {
    final fakeActions = _FakePerfilActions();

    await pumpPerfil(
      tester,
      perfil: _perfil(fotoB64: _validPhotoB64),
      overrides: [
        perfilActionsProvider.overrideWith((ref) => fakeActions),
      ],
    );

    await tester.tap(find.byIcon(Icons.camera_alt));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Remover foto atual'));
    await tester.pumpAndSettle();

    expect(fakeActions.removerFotoCalls, 1);
    expect(find.text('Foto removida.'), findsOneWidget);
  });

  testWidgets('gps recente chip is hidden when last gps timestamp is stale',
      (tester) async {
    await pumpPerfil(
      tester,
      perfil: _perfil(
        lastGpsTs: DateTime.now()
            .subtract(const Duration(days: 2))
            .toUtc()
            .toIso8601String(),
      ),
    );

    expect(find.text('GPS recente'), findsNothing);
  });

  testWidgets('gps recente chip is shown when last gps timestamp is fresh',
      (tester) async {
    await pumpPerfil(
      tester,
      perfil: _perfil(
        lastGpsTs: DateTime.now()
            .subtract(const Duration(hours: 1))
            .toUtc()
            .toIso8601String(),
      ),
    );

    expect(find.text('GPS recente'), findsOneWidget);
  });
}
