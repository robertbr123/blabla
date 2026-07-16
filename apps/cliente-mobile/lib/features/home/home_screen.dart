import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:go_router/go_router.dart';

import '../../core/api/dto.dart';
import '../../core/api/me_repository.dart';
import '../../core/api/os_repository.dart';
import '../../core/api/promocoes_repository.dart';
import '../../core/api/rede_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/cache/last_known_cache.dart';
import '../../core/contrato/contrato_atual_provider.dart';
import '../../core/api/card_dia_repository.dart';
import '../../core/api/contatos_repository.dart';
import '../../core/api/fidelidade_repository.dart';
import '../../core/api/streak_repository.dart';
import '../../core/api/manutencoes_repository.dart';
import '../nps/nps_bottom_sheet.dart';
import '../shell/main_shell.dart';
import 'widgets/aniversariante_banner.dart';
import 'widgets/avisos_list.dart';
import 'widgets/card_do_dia.dart';
import 'widgets/contrato_switcher.dart';
import 'widgets/fatura_card.dart';
import 'widgets/home_capa.dart';
import 'widgets/manutencao_breaking_bar.dart';
import 'widgets/promo_carousel.dart';
import 'widgets/quick_actions.dart';
import 'widgets/quick_cards_row.dart';
import 'widgets/streak_badge.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  /// Set de OS ids pra quais já mostramos o popup nesta sessão.
  /// Evita reaparecer toda vez que a Home re-renderiza ou o user volta na tab.
  final _npsAlreadyPromptedThisSession = <String>{};

  @override
  Widget build(BuildContext context) {
    final meAsync = ref.watch(meProvider);
    final avisosAsync = ref.watch(avisosProvider);
    final promosAsync = ref.watch(promocoesProvider);
    final redeAsync = ref.watch(redeAparelhosProvider);
    final topInset = MediaQuery.paddingOf(context).top;
    // Clampa a fonte do sistema a no máximo 1.2x pros offsets/extents
    // fixos do header colapsável escalarem sem cortar texto (fontes bem
    // grandes ainda entram no espaço, só que colapsam menos).
    final fontScale =
        MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.2).scale(1.0);

    // Auto-popup de NPS pendente: quando a lista de OS chega, se houver
    // alguma com npsPendente que ainda nao foi mostrada nesta sessao,
    // abre o bottom sheet automaticamente.
    ref.listen<AsyncValue<List<OsDto>>>(osListProvider, (_, next) {
      next.whenData(_maybePromptNps);
    });

    final rede = redeAsync.maybeWhen(
      data: (d) => d.encontrada ? d : null,
      orElse: () => null,
    );

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        edgeOffset: topInset + HomeCapaDelegate.expandedExtra,
        child: CustomScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          slivers: [
            // ── Capa colapsável (fixa ao rolar) ──
            meAsync.when(
              data: (me) {
                _persistMe(me);
                final contratoAtual = _contratoAtual(me);
                return SliverPersistentHeader(
                  pinned: true,
                  delegate: HomeCapaDelegate(
                    topInset: topInset,
                    fontScale: fontScale,
                    me: me,
                    rede: rede,
                    contratoAtual: contratoAtual,
                    podeTrocarContrato: me.temMultiContrato,
                    onTrocarContrato: (ctx) =>
                        showContratoSelector(ctx, ref, me),
                  ),
                );
              },
              loading: () => SliverPersistentHeader(
                pinned: true,
                delegate: HomeCapaDelegate(
                  topInset: topInset,
                  fontScale: fontScale,
                  loading: true,
                ),
              ),
              error: (_, __) => _CachedCapaHeader(
                topInset: topInset,
                fontScale: fontScale,
              ),
            ),
            // ── Folha (cor chapada — o canto arredondado já foi pintado
            // dentro do header, no lábio da folha) ──
            _folhaFiller(
              context,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  BrandTokens.spaceLg,
                  BrandTokens.spaceLg,
                  BrandTokens.spaceLg,
                  120,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const ManutencaoBreakingBar(),
                    const FaturaCard(),
                    const StreakBadge(),
                    const _SectionLabel(label: 'Ações rapidas'),
                    const SizedBox(height: BrandTokens.spaceSm),
                    QuickActions(
                      actions: [
                        QuickAction(
                          icon: Icons.wifi_rounded,
                          label: 'Minha rede',
                          color: BrandTokens.primary,
                          onTap: () => context.push('/rede'),
                        ),
                        QuickAction(
                          icon: Icons.receipt_long_outlined,
                          label: '2a via',
                          color: BrandTokens.catBilling,
                          onTap: () => ref
                              .read(mainShellTabProvider.notifier)
                              .state = 1,
                        ),
                        QuickAction(
                          icon: Icons.support_agent_outlined,
                          label: 'Falar conosco',
                          color: BrandTokens.catSupport,
                          onTap: () => ref
                              .read(mainShellTabProvider.notifier)
                              .state = 2,
                        ),
                        QuickAction(
                          icon: Icons.wifi_off_outlined,
                          label: 'Sem internet',
                          color: BrandTokens.catConnection,
                          onTap: () => context.push('/suporte/novo'),
                        ),
                        QuickAction(
                          icon: Icons.swap_horiz_rounded,
                          label: 'Mudar plano',
                          color: BrandTokens.catPlan,
                          onTap: () => context.push('/suporte/novo'),
                        ),
                      ],
                    ),
                    const SizedBox(height: BrandTokens.spaceLg),
                    const QuickCardsRow(),
                    const CardDoDia(),
                    ...promosAsync.when(
                      data: (promos) {
                        if (promos.isEmpty) return const <Widget>[];
                        return [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const _SectionLabel(label: 'Pra você'),
                              if (promos.length > 1)
                                TextButton(
                                  onPressed: () => context.push('/promocoes'),
                                  child: const Text('Ver todas →'),
                                ),
                            ],
                          ),
                          const SizedBox(height: BrandTokens.spaceSm),
                          PromoCarousel(items: promos),
                          const SizedBox(height: BrandTokens.spaceLg),
                        ];
                      },
                      loading: () => const <Widget>[],
                      error: (_, __) => const <Widget>[],
                    ),
                    meAsync.maybeWhen(
                      data: (me) => AniversarianteBanner(me: me),
                      orElse: () => const SizedBox.shrink(),
                    ),
                    avisosAsync.when(
                      data: (a) => AvisosList(avisos: a),
                      loading: () => const SizedBox.shrink(),
                      error: (_, __) => const SizedBox.shrink(),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  ContratoResumoDto? _contratoAtual(MeDto me) {
    if (me.contratos.isEmpty) return null;
    final id = ref.watch(contratoAtualProvider);
    return me.contratos.firstWhere(
      (c) => c.id == id,
      orElse: () => me.contratos.first,
    );
  }

  Future<void> _onRefresh() async {
    // Força invalidação do cache SGP no backend antes de re-fetchar,
    // pra mudancas de SGP (contratos novos, plano, etc) aparecerem.
    try {
      final contratoId = ref.read(contratoAtualProvider);
      await ref
          .read(meRepositoryProvider)
          .refresh(contratoId: contratoId);
    } on Object {
      // best-effort — segue invalidando providers de qualquer forma
    }
    ref.invalidate(meProvider);
    ref.invalidate(avisosProvider);
    ref.invalidate(promocoesProvider);
    ref.invalidate(osListProvider);
    ref.invalidate(manutencoesAtivasProvider);
    ref.invalidate(fidelidadeProvider);
    ref.invalidate(contatosOperadoraProvider);
    ref.invalidate(cardDiaProvider);
    ref.invalidate(streakProvider);
    ref.invalidate(redeAparelhosProvider);
    await ref.read(meProvider.future);
  }

  void _maybePromptNps(List<OsDto> osList) {
    // Escolhe a OS mais recente com NPS pendente nao mostrada ainda.
    OsDto? alvo;
    for (final o in osList) {
      if (!o.npsPendente) continue;
      if (_npsAlreadyPromptedThisSession.contains(o.id)) continue;
      if (alvo == null || o.updatedAt.isAfter(alvo.updatedAt)) {
        alvo = o;
      }
    }
    if (alvo == null) return;
    final id = alvo.id;
    final tipoLabel = alvo.tipoLabel;
    final numero = _numeroCurto(id);
    final teveVisita = alvo.teveVisitaTecnica;
    _npsAlreadyPromptedThisSession.add(id);
    // Aguarda o frame atual concluir pra evitar showModalBottomSheet durante build.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      showNpsBottomSheet(
        context,
        osId: id,
        tipoLabel: tipoLabel,
        numero: numero,
        teveVisitaTecnica: teveVisita,
      ).then((_) {
        // Apos o sheet fechar (com ou sem submit), invalida pra refletir
        // npsRespondidoEm caso o user tenha enviado.
        ref.invalidate(osListProvider);
      });
    });
  }

  String _numeroCurto(String osId) {
    final clean = osId.replaceAll('-', '');
    return clean.length <= 6
        ? clean.toUpperCase()
        : clean.substring(0, 6).toUpperCase();
  }

  Future<void> _persistMe(MeDto me) async {
    await LastKnownCache().writeMe(me);
  }
}

// ════════ Sliver da folha (cor chapada, sem canto) ════════
//
// Os cantos arredondados da folha são pintados DENTRO do header (lábio no
// fundo do HomeCapaDelegate), sobre o próprio gradiente — assim capa e
// canto se encontram perfeitamente em qualquer shrinkOffset e nunca existe
// fresta/corte azul. Aqui embaixo a folha é só um container chapado que
// continua a mesma cor do lábio (mesmo padrão do PerfilScreen).
Widget _folhaFiller(
  BuildContext context, {
  required Widget child,
  double minHeight = 0,
}) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  return SliverToBoxAdapter(
    child: Container(
      constraints: BoxConstraints(minHeight: minHeight),
      color: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      child: child,
    ),
  );
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: -0.2,
          ),
    );
  }
}

/// Capa colapsável pra quando `meProvider` falha: tenta o último `me`
/// conhecido em cache (mostra o header normal) e, sem cache nenhum, mostra
/// o header em modo de erro com botão de retry.
class _CachedCapaHeader extends ConsumerWidget {
  const _CachedCapaHeader({required this.topInset, required this.fontScale});
  final double topInset;
  final double fontScale;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<MeDto?>(
      future: LastKnownCache().readMe(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return SliverPersistentHeader(
            pinned: true,
            delegate: HomeCapaDelegate(
              topInset: topInset,
              fontScale: fontScale,
              loading: true,
            ),
          );
        }
        final me = snap.data;
        if (me == null) {
          return SliverPersistentHeader(
            pinned: true,
            delegate: HomeCapaDelegate(
              topInset: topInset,
              fontScale: fontScale,
              errorMode: true,
              onRetry: () => ref.invalidate(meProvider),
            ),
          );
        }
        final redeAsync = ref.watch(redeAparelhosProvider);
        final rede = redeAsync.maybeWhen(
          data: (d) => d.encontrada ? d : null,
          orElse: () => null,
        );
        final contratoId = ref.watch(contratoAtualProvider);
        final contratoAtual = me.contratos.isEmpty
            ? null
            : me.contratos.firstWhere(
                (c) => c.id == contratoId,
                orElse: () => me.contratos.first,
              );
        return SliverPersistentHeader(
          pinned: true,
          delegate: HomeCapaDelegate(
            topInset: topInset,
            fontScale: fontScale,
            me: me,
            rede: rede,
            contratoAtual: contratoAtual,
            podeTrocarContrato: me.temMultiContrato,
            onTrocarContrato: (ctx) => showContratoSelector(ctx, ref, me),
          ),
        );
      },
    );
  }
}
