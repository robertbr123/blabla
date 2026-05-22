import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_state.dart';
import 'features/auth/login_screen.dart';
import 'features/conexao/conexao_screen.dart';
import 'features/faq/faq_artigo_screen.dart';
import 'features/faq/faq_screen.dart';
import 'features/indicacao/indicacao_screen.dart';
import 'features/legal/legal_screen.dart';
import 'features/notificacoes/notif_prefs_screen.dart';
import 'features/notificacoes/notificacoes_screen.dart';
import 'features/onboarding/onboarding_biometric_screen.dart';
import 'features/onboarding/onboarding_cpf_screen.dart';
import 'features/onboarding/onboarding_otp_screen.dart';
import 'features/onboarding/onboarding_password_screen.dart';
import 'features/perfil/editar_perfil_screen.dart';
import 'features/perfil/mudar_senha_screen.dart';
import 'features/suporte/novo_chamado_screen.dart';
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
      GoRoute(
        path: '/suporte/novo',
        builder: (_, __) => const NovoChamadoScreen(),
      ),
      GoRoute(
        path: '/indicacao',
        builder: (_, __) => const IndicacaoScreen(),
      ),
      GoRoute(
        path: '/conexao',
        builder: (_, __) => const ConexaoScreen(),
      ),
      GoRoute(
        path: '/notificacoes',
        builder: (_, __) => const NotificacoesScreen(),
      ),
      GoRoute(
        path: '/notificacoes/preferencias',
        builder: (_, __) => const NotifPrefsScreen(),
      ),
      GoRoute(
        path: '/faq',
        builder: (_, __) => const FaqScreen(),
      ),
      GoRoute(
        path: '/faq/:artigoId',
        builder: (_, state) =>
            FaqArtigoScreen(artigoId: state.pathParameters['artigoId']!),
      ),
      GoRoute(
        path: '/legal/termos',
        builder: (_, __) => const LegalScreen(
          title: 'Termos de Uso',
          body: termosUsoBody,
        ),
      ),
      GoRoute(
        path: '/legal/privacidade',
        builder: (_, __) => const LegalScreen(
          title: 'Politica de Privacidade',
          body: politicaPrivacidadeBody,
        ),
      ),
    ],
  );
});
