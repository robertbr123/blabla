import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_state.dart';
import 'features/auth/login_screen.dart';
import 'features/onboarding/onboarding_biometric_screen.dart';
import 'features/onboarding/onboarding_cpf_screen.dart';
import 'features/onboarding/onboarding_otp_screen.dart';
import 'features/onboarding/onboarding_password_screen.dart';
import 'features/perfil/editar_perfil_screen.dart';
import 'features/perfil/mudar_senha_screen.dart';
import 'features/shell/main_shell.dart';
import 'features/splash/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: ref.watch(authRefreshProvider),
    redirect: (context, state) async {
      final loc = state.matchedLocation;
      if (loc == '/splash') return null;

      bool has = false;
      try {
        has = await ref
            .read(hasTokenProvider.future)
            .timeout(const Duration(seconds: 3), onTimeout: () => false);
      } catch (_) {}

      final inAuthArea = loc.startsWith('/onboarding') || loc == '/login';
      if (!has && !inAuthArea) return '/onboarding/cpf';
      if (has && inAuthArea) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/onboarding/cpf',
        builder: (_, __) => const OnboardingCpfScreen(),
      ),
      GoRoute(
        path: '/onboarding/otp',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return OnboardingOtpScreen(
            cpf: extra?['cpf'] ?? '',
            maskedPhone: extra?['masked_phone'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/onboarding/password',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return OnboardingPasswordScreen(
            setupToken: extra?['setup_token'] ?? '',
            cpf: extra?['cpf'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/onboarding/biometric',
        builder: (_, __) => const OnboardingBiometricScreen(),
      ),
      GoRoute(path: '/home', builder: (_, __) => const MainShell()),
      GoRoute(
        path: '/perfil/editar',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return EditarPerfilScreen(
            campo: extra?['campo'] ?? 'telefone',
            valor: extra?['valor'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/perfil/mudar-senha',
        builder: (_, __) => const MudarSenhaScreen(),
      ),
    ],
  );
});
