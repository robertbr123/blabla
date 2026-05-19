import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_repository.dart';
import 'features/auth/login_screen.dart';
import 'features/os/os_detail_screen.dart';
import 'features/os/os_list_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/os',
    redirect: (context, state) async {
      final has = await ref.read(hasTokenProvider.future);
      final goingToLogin = state.matchedLocation == '/login';
      if (!has && !goingToLogin) return '/login';
      if (has && goingToLogin) return '/os';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/os', builder: (_, __) => const OsListScreen()),
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
