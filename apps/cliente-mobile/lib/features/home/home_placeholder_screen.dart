import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class HomePlaceholderScreen extends ConsumerWidget {
  const HomePlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionSnapshotProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inicio'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(authRepositoryProvider).logout();
              ref.read(authRefreshProvider).bump();
              if (context.mounted) context.go('/onboarding/cpf');
            },
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceXl),
          child: session.when(
            data: (s) => Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.check_circle_outline,
                    color: BrandTokens.success, size: 72),
                const SizedBox(height: BrandTokens.spaceMd),
                Text(
                  'Voce esta dentro!',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
                Text(
                  s == null
                      ? 'Sem sessao'
                      : 'CPF ***.***.***-${s.cpfLast4}',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: BrandTokens.spaceLg),
                Text(
                  'Suas faturas, plano e suporte chegam aqui nas proximas fases.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
              ],
            ),
            loading: () => const CircularProgressIndicator(),
            error: (_, __) => const Text('Erro carregando sessao'),
          ),
        ),
      ),
    );
  }
}
