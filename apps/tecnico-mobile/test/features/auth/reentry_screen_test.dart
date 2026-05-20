import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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

Widget _buildRouterApp({
  required bool hasToken,
  SessionSnapshot? session,
}) {
  return ProviderScope(
    overrides: [
      hasTokenProvider.overrideWith((ref) => Future<bool>.value(hasToken)),
      sessionSnapshotProvider.overrideWith(
        (ref) => Future<SessionSnapshot?>.value(session),
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
    await tester.pumpWidget(
      _buildRouterApp(
        hasToken: true,
        session: const SessionSnapshot(
          userId: 'u1',
          role: 'tecnico',
          nome: 'Roberto',
          biometricEnabled: true,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();

    expect(find.text('Entrar com Face ID'), findsOneWidget);
    expect(find.text('Roberto'), findsOneWidget);
  });

  testWidgets('reentry screen fallback opens full login', (tester) async {
    await tester.pumpWidget(
      _buildRouterApp(
        hasToken: true,
        session: const SessionSnapshot(
          userId: 'u1',
          role: 'tecnico',
          nome: 'Roberto',
          biometricEnabled: true,
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

  testWidgets('splash routes to login when there is no token', (tester) async {
    await tester.pumpWidget(_buildRouterApp(hasToken: false));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();

    expect(find.text('Bem-vindo'), findsOneWidget);
    expect(find.text('Entrar'), findsOneWidget);
  });

  testWidgets('splash routes to os when token has no biometric snapshot',
      (tester) async {
    await tester.pumpWidget(_buildRouterApp(hasToken: true));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('OS'), findsOneWidget);
    expect(find.text('Entrar com Face ID'), findsNothing);
  });

  testWidgets('reentry screen redirects to os when session is unavailable',
      (tester) async {
    final router = GoRouter(
      initialLocation: '/reentry',
      routes: [
        GoRoute(
          path: '/reentry',
          builder: (_, __) => const ReentryScreen(),
        ),
        GoRoute(
          path: '/os',
          builder: (_, __) => const Scaffold(body: Text('Tela OS')),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sessionSnapshotProvider.overrideWith(
            (ref) => Future<SessionSnapshot?>.value(null),
          ),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('Tela OS'), findsOneWidget);
  });
}
