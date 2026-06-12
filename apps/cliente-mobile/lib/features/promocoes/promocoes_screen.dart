import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/dto.dart';
import '../../core/api/promocoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/async_states.dart';
import '../../core/ui/glass_app_bar.dart';
import 'widgets/promo_card.dart';

/// Página dedicada de promoções: vitrine em lista vertical.
/// Tap no card registra click e navega pra landing de detalhe.
class PromocoesScreen extends ConsumerWidget {
  const PromocoesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(promocoesProvider);
    final topPad =
        MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: const GlassAppBar(title: 'Promoções'),
      body: RefreshIndicator(
        edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight,
        onRefresh: () async {
          ref.invalidate(promocoesProvider);
          await ref.read(promocoesProvider.future);
        },
        child: AsyncBuilder<List<PromocaoDto>>(
          value: async,
          loading: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.only(top: topPad),
            children: const [Center(child: CircularProgressIndicator())],
          ),
          error: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
              BrandTokens.spaceMd,
              topPad,
              BrandTokens.spaceMd,
              BrandTokens.spaceMd,
            ),
            children: [
              ErrorCard(onRetry: () => ref.invalidate(promocoesProvider)),
            ],
          ),
          builder: (promos) {
            if (promos.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.only(top: topPad),
                children: const [
                  EmptyState(
                    icon: Icons.local_offer_outlined,
                    title: 'Nenhuma promoção no momento',
                    subtitle: 'Quando rolar novidade boa, ela aparece aqui.',
                  ),
                ],
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: EdgeInsets.fromLTRB(
                BrandTokens.spaceMd,
                topPad,
                BrandTokens.spaceMd,
                BrandTokens.spaceXl,
              ),
              itemCount: promos.length,
              separatorBuilder: (_, __) =>
                  const SizedBox(height: BrandTokens.spaceMd),
              itemBuilder: (ctx, i) => SizedBox(
                height: 172,
                child: PromoCard(
                  item: promos[i],
                  onTap: (p) {
                    ref
                        .read(promocoesRepositoryProvider)
                        .registrarEvento(p.id, 'click');
                    ctx.push('/promocoes/${p.id}');
                  },
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
