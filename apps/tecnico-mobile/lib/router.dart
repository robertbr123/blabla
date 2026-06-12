import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_repository.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/reentry_screen.dart';
import 'features/clientes/cliente_detail_screen.dart';
import 'features/clientes/cliente_novo_screen.dart';
import 'features/rede/rede_screen.dart';
import 'features/design_preview/design_preview_screen.dart';
import 'features/os/os_detail_screen.dart';
import 'features/shell/main_shell.dart';
import 'features/splash/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: ref.watch(authRefreshListenableProvider),
    redirect: (context, state) async {
      final loc = state.matchedLocation;
      // Splash decide pra onde mandar — nao redireciona.
      if (loc == '/splash') return null;
      // Preview de design — só em debug, acesso livre sem auth.
      if (kDebugMode && loc == '/design-preview') return null;
      // Defensivo: storage com timeout pra nao travar a navegacao.
      bool has = false;
      try {
        has = await ref
            .read(hasTokenProvider.future)
            .timeout(const Duration(seconds: 3), onTimeout: () => false);
      } catch (_) {}
      bool biometric = false;
      try {
        final session = await ref
            .read(sessionSnapshotProvider.future)
            .timeout(const Duration(seconds: 3), onTimeout: () => null);
        biometric = session?.biometricEnabled ?? false;
      } catch (_) {}
      final goingToLogin = loc == '/login';
      final goingToReentry = loc == '/reentry';
      if (!has) {
        return goingToLogin ? null : '/login';
      }
      if (goingToReentry && !biometric) {
        return '/os';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      // Preview de design registrada apenas em builds debug.
      if (kDebugMode)
        GoRoute(
          path: '/design-preview',
          builder: (_, __) => const DesignPreviewScreen(),
        ),
      GoRoute(path: '/reentry', builder: (_, __) => const ReentryScreen()),
      GoRoute(
        path: '/os',
        builder: (_, __) => const MainShell(initialTab: 0),
      ),
      GoRoute(
        path: '/estoque',
        builder: (_, __) => const MainShell(initialTab: 1),
      ),
      GoRoute(
        path: '/clientes',
        builder: (_, __) => const MainShell(initialTab: 2),
      ),
      GoRoute(
        path: '/perfil',
        builder: (_, __) => const MainShell(initialTab: 3),
      ),
      GoRoute(
        path: '/os/:id',
        builder: (_, st) => OsDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(
        path: '/clientes/novo',
        builder: (_, __) => const ClienteNovoScreen(),
      ),
      GoRoute(
        path: '/clientes/:id',
        builder: (_, st) => ClienteDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(
        path: '/rede/:cpf',
        builder: (_, st) => RedeScreen(cpf: st.pathParameters['cpf']!),
      ),
    ],
    errorBuilder: (_, st) => Scaffold(
      body: Center(child: Text('Rota não encontrada: ${st.matchedLocation}')),
    ),
  );
});
