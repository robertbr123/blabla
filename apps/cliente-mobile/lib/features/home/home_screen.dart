import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:go_router/go_router.dart';

import '../../core/api/dto.dart';
import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/cache/last_known_cache.dart';
import '../shell/main_shell.dart';
import 'widgets/avisos_list.dart';
import 'widgets/hero_card.dart';
import 'widgets/quick_actions.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final avisosAsync = ref.watch(avisosProvider);

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(meProvider);
            ref.invalidate(avisosProvider);
            await ref.read(meProvider.future);
          },
          child: ListView(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            children: [
              meAsync.when(
                data: (me) {
                  _persistMe(me);
                  return HeroCard(me: me);
                },
                loading: () => const _HeroSkeleton(),
                error: (_, __) => _CachedHeroOrError(ref),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              QuickActions(
                actions: [
                  QuickAction(
                    icon: Icons.receipt_long_outlined,
                    label: '2a via',
                    onTap: () =>
                        ref.read(mainShellTabProvider.notifier).state = 1,
                  ),
                  QuickAction(
                    icon: Icons.support_agent_outlined,
                    label: 'Falar conosco',
                    onTap: () =>
                        ref.read(mainShellTabProvider.notifier).state = 2,
                  ),
                  QuickAction(
                    icon: Icons.wifi_off_outlined,
                    label: 'Sem internet',
                    onTap: () => context.push('/suporte/novo'),
                  ),
                  QuickAction(
                    icon: Icons.swap_horiz,
                    label: 'Mudar plano',
                    onTap: () => context.push('/suporte/novo'),
                  ),
                ],
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              avisosAsync.when(
                data: (a) => AvisosList(avisos: a),
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
              ),
              const SizedBox(height: BrandTokens.spaceXl),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _persistMe(MeDto me) async {
    await LastKnownCache().writeMe(me);
  }
}

class _HeroSkeleton extends StatelessWidget {
  const _HeroSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 160,
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      ),
      child: const Center(child: CircularProgressIndicator()),
    );
  }
}

class _CachedHeroOrError extends StatelessWidget {
  const _CachedHeroOrError(this.ref);
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MeDto?>(
      future: LastKnownCache().readMe(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const _HeroSkeleton();
        }
        final me = snap.data;
        if (me != null) return HeroCard(me: me);
        return Container(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          decoration: BoxDecoration(
            color: BrandTokens.danger.withOpacity(0.08),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          ),
          child: Column(
            children: [
              const Icon(Icons.error_outline, color: BrandTokens.danger),
              const SizedBox(height: BrandTokens.spaceSm),
              const Text('Nao conseguimos carregar seus dados.'),
              TextButton(
                onPressed: () => ref.invalidate(meProvider),
                child: const Text('Tentar de novo'),
              ),
            ],
          ),
        );
      },
    );
  }
}
