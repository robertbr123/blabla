import 'package:flutter/material.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_state.dart';
import 'features/auth/forgot_reset_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/conexao/conexao_screen.dart';
import 'features/rede/rede_screen.dart';
import 'features/contatos/contatos_screen.dart';
import 'features/faq/faq_artigo_screen.dart';
import 'features/fidelidade/fidelidade_screen.dart';
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
import 'features/promocoes/promocoes_screen.dart';
import 'features/shell/main_shell.dart' show MainShell, mainShellTabProvider;
import 'features/splash/splash_screen.dart';

/// Chave global do Navigator raiz. Usada pra navegar de fora da arvore de
/// widgets (ex: tap numa notificacao push, em [PushService]).
final rootNavigatorKey = GlobalKey<NavigatorState>();

/// Transição padrão das telas internas: fade + slide sutil (curva iOS).
CustomTransitionPage<void> _glassPage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 320),
    reverseTransitionDuration: const Duration(milliseconds: 280),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(
        parent: animation,
        curve: const Cubic(0.32, 0.72, 0, 1),
      );
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0.04, 0),
            end: Offset.zero,
          ).animate(curved),
          child: child,
        ),
      );
    },
  );
}

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    navigatorKey: rootNavigatorKey,
    refreshListenable: ref.watch(authRefreshProvider),
    // Fallback gracioso pra qualquer rota desconhecida (deep link mal formado,
    // link velho, etc) — joga pra /home em vez de mostrar GoException feia.
    // O redirect global ainda decide pra onde levar (onboarding se nao logado,
    // /home se logado).
    errorBuilder: (context, state) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) context.go('/home');
      });
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    },
    redirect: (context, state) async {
      final loc = state.matchedLocation;
      if (loc == '/splash') return null;

      bool has = false;
      try {
        has = await ref
            .read(hasTokenProvider.future)
            .timeout(const Duration(seconds: 3), onTimeout: () => false);
      } catch (_) {}

      final inAuthArea = loc.startsWith('/onboarding') ||
          loc.startsWith('/forgot') ||
          loc == '/login';
      if (!has && !inAuthArea) return '/onboarding/cpf';
      if (has && inAuthArea) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/forgot/reset',
        builder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return ForgotResetScreen(
            cpf: extra?['cpf'] ?? '',
            maskedPhone: extra?['masked_phone'] ?? '',
          );
        },
      ),
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
      // App Links: botoes "Ver no app" dos templates WhatsApp aterrissam
      // aqui. Setam a tab certa do shell e redirecionam pra /home pra
      // reusar o MainShell. Se usuario nao estiver logado, o redirect global
      // bate antes e manda pro onboarding (tab fica setada pra quando logar).
      GoRoute(
        path: '/faturas',
        redirect: (context, state) {
          ref.read(mainShellTabProvider.notifier).state = 1;
          return '/home';
        },
      ),
      GoRoute(
        path: '/suporte',
        redirect: (context, state) {
          ref.read(mainShellTabProvider.notifier).state = 2;
          return '/home';
        },
      ),
      GoRoute(
        path: '/perfil/editar',
        pageBuilder: (_, state) {
          final extra = state.extra as Map<String, String>?;
          return _glassPage(
            state,
            EditarPerfilScreen(
              campo: extra?['campo'] ?? 'telefone',
              valor: extra?['valor'] ?? '',
            ),
          );
        },
      ),
      GoRoute(
        path: '/perfil/mudar-senha',
        pageBuilder: (_, state) => _glassPage(state, const MudarSenhaScreen()),
      ),
      GoRoute(
        path: '/suporte/novo',
        pageBuilder: (_, state) =>
            _glassPage(state, const NovoChamadoScreen()),
      ),
      GoRoute(
        path: '/indicacao',
        pageBuilder: (_, state) => _glassPage(state, const IndicacaoScreen()),
      ),
      GoRoute(
        path: '/conexao',
        pageBuilder: (_, state) => _glassPage(state, const ConexaoScreen()),
      ),
      GoRoute(
        path: '/rede',
        pageBuilder: (_, state) => _glassPage(state, const RedeScreen()),
      ),
      GoRoute(
        path: '/promocoes',
        pageBuilder: (_, state) => _glassPage(state, const PromocoesScreen()),
      ),
      GoRoute(
        path: '/notificacoes',
        pageBuilder: (_, state) =>
            _glassPage(state, const NotificacoesScreen()),
      ),
      GoRoute(
        path: '/notificacoes/preferencias',
        pageBuilder: (_, state) =>
            _glassPage(state, const NotifPrefsScreen()),
      ),
      GoRoute(
        path: '/contatos',
        pageBuilder: (_, state) => _glassPage(state, const ContatosScreen()),
      ),
      GoRoute(
        path: '/fidelidade',
        pageBuilder: (_, state) => _glassPage(state, const FidelidadeScreen()),
      ),
      GoRoute(
        path: '/faq',
        pageBuilder: (_, state) => _glassPage(state, const FaqScreen()),
      ),
      GoRoute(
        path: '/faq/:artigoId',
        pageBuilder: (_, state) => _glassPage(
          state,
          FaqArtigoScreen(artigoId: state.pathParameters['artigoId']!),
        ),
      ),
      GoRoute(
        path: '/legal/termos',
        pageBuilder: (_, state) => _glassPage(
          state,
          const LegalScreen(
            title: 'Termos de Uso',
            body: termosUsoBody,
          ),
        ),
      ),
      GoRoute(
        path: '/legal/privacidade',
        pageBuilder: (_, state) => _glassPage(
          state,
          const LegalScreen(
            title: 'Politica de Privacidade',
            body: politicaPrivacidadeBody,
          ),
        ),
      ),
    ],
  );
});
