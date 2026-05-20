import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tecnico_mobile/core/auth/auth_repository.dart';
import 'package:tecnico_mobile/core/auth/session_state.dart';
import 'package:tecnico_mobile/features/auth/reentry_screen.dart';
import 'package:tecnico_mobile/router.dart';

Widget _buildReentryApp({required String nome}) {
  return ProviderScope(
    overrides: [
      sessionSnapshotProvider.overrideWith(
        (ref) => Future<SessionSnapshot?>.value(
          SessionSnapshot(
            userId: 'u1',
            role: 'tecnico',
            nome: nome,
            biometricEnabled: true,
          ),
        ),
      ),
    ],
    child: const MaterialApp(home: ReentryScreen()),
  );
}

Widget _buildRouterApp() {
  return ProviderScope(
    overrides: [
      hasTokenProvider.overrideWith((ref) => Future<bool>.value(true)),
      sessionSnapshotProvider.overrideWith(
        (ref) => Future<SessionSnapshot?>.value(
          const SessionSnapshot(
            userId: 'u1',
            role: 'tecnico',
            nome: 'Roberto',
            biometricEnabled: true,
          ),
        ),
      ),
    ],
    child: Consumer(
      builder: (context, ref, _) {
        return MaterialApp.router(
          routerConfig: ref.watch(routerProvider),
        );
      },
    ),
  );
}

void main() {
  testWidgets('reentry screen shows technician name and Face ID action',
      (tester) async {
    await tester.pumpWidget(_buildReentryApp(nome: 'Roberto'));
    await tester.pumpAndSettle();

    expect(find.text('Roberto'), findsOneWidget);
    expect(find.text('Entrar com Face ID'), findsOneWidget);
    expect(find.text('Entrar com email e senha'), findsOneWidget);
  });

  testWidgets('splash routes to reentry when token and biometric session exist',
      (tester) async {
    await tester.pumpWidget(_buildRouterApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();

    expect(find.text('Entrar com Face ID'), findsOneWidget);
    expect(find.text('Roberto'), findsOneWidget);
  });

  testWidgets('reentry screen fallback opens full login', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          hasTokenProvider.overrideWith((ref) => Future<bool>.value(true)),
          sessionSnapshotProvider.overrideWith(
            (ref) => Future<SessionSnapshot?>.value(
              const SessionSnapshot(
                userId: 'u1',
                role: 'tecnico',
                nome: 'Roberto',
                biometricEnabled: true,
              ),
            ),
          ),
        ],
        child: Consumer(
          builder: (context, ref, _) {
            return MaterialApp.router(
              routerConfig: ref.watch(routerProvider),
            );
          },
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Entrar com email e senha'));
    await tester.pumpAndSettle();

    expect(find.text('Bem-vindo'), findsOneWidget);
    expect(find.text('Entrar'), findsOneWidget);
  });
}
