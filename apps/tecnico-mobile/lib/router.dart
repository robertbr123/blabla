import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_repository.dart';
import 'features/auth/login_screen.dart';
import 'features/os/os_detail_screen.dart';
import 'features/shell/main_shell.dart';
import 'features/splash/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) async {
      final loc = state.matchedLocation;
      // Splash decide pra onde mandar — nao redireciona.
      if (loc == '/splash') return null;
      final has = await ref.read(hasTokenProvider.future);
      final goingToLogin = loc == '/login';
      if (!has && !goingToLogin) return '/login';
      if (has && goingToLogin) return '/os';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/os',
        builder: (_, __) => const MainShell(initialTab: 0),
      ),
      GoRoute(
        path: '/estoque',
        builder: (_, __) => const MainShell(initialTab: 1),
      ),
      GoRoute(
        path: '/perfil',
        builder: (_, __) => const MainShell(initialTab: 2),
      ),
      GoRoute(
        path: '/os/:id',
        builder: (_, st) => OsDetailScreen(id: st.pathParameters['id']!),
      ),
    ],
    errorBuilder: (_, st) => Scaffold(
      body: Center(child: Text('Rota não encontrada: ${st.matchedLocation}')),
    ),
  );
});
