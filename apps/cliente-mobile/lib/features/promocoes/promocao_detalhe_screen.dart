import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/api/dto.dart';
import '../../core/api/promocoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/contrato/contrato_atual_provider.dart';
import '../../core/ui/async_states.dart';
import '../../core/ui/hex_color.dart';
import '../home/promo_icon_map.dart';

/// Landing CTA da promoção: hero com o gradiente do card, descrição longa,
/// regras expansíveis e botão fixo de ação ("Tenho interesse" → lead, ou a
/// ação original quando a promo tem cta de url/tela — ex: indicacao).
class PromocaoDetalheScreen extends ConsumerStatefulWidget {
  const PromocaoDetalheScreen({super.key, required this.promoId});
  final String promoId;

  @override
  ConsumerState<PromocaoDetalheScreen> createState() =>
      _PromocaoDetalheScreenState();
}

enum _CtaState { idle, sending, done }

class _PromocaoDetalheScreenState
    extends ConsumerState<PromocaoDetalheScreen> {
  _CtaState _cta = _CtaState.idle;
  bool _viewTracked = false;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(promocaoDetalheProvider(widget.promoId));

    // Tracking de view do detalhe (1x por abertura, fire-and-forget).
    async.whenData((p) {
      if (!_viewTracked) {
        _viewTracked = true;
        ref
            .read(promocoesRepositoryProvider)
            .registrarEvento(p.id, 'detail_view');
      }
    });

    return Scaffold(
      body: AsyncBuilder<PromocaoDetalheDto>(
        value: async,
        loading: const Center(child: CircularProgressIndicator()),
        error: Center(
          child: Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            child: ErrorCard(
              message: 'Não conseguimos abrir essa promoção agora.',
              onRetry: () =>
                  ref.invalidate(promocaoDetalheProvider(widget.promoId)),
            ),
          ),
        ),
        builder: (p) => _Conteudo(
          promo: p,
          cta: p.interesseRegistrado ? _CtaState.done : _cta,
          onCta: () => _executarCta(p),
        ),
      ),
    );
  }

  Future<void> _executarCta(PromocaoDetalheDto p) async {
    final action = p.ctaAction;
    // Promo com ação própria (indicacao, url externa, tela) → executa a
    // ação original em vez de gerar lead. Não quebra o que existe.
    if (action.startsWith('tela:')) {
      context.push(action.substring(5));
      return;
    }
    if (action.startsWith('url:')) {
      final uri = Uri.tryParse(action.substring(4));
      if (uri != null) {
        try {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        } catch (_) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Não conseguimos abrir o link agora.'),
            ),
          );
        }
      }
      return;
    }
    // "info" → lead "Tenho interesse".
    if (_cta != _CtaState.idle) return;
    setState(() => _cta = _CtaState.sending);
    try {
      // contratoAtualProvider é StateNotifierProvider<ContratoAtualNotifier, String?>
      // — o estado é diretamente String? (o id do contrato selecionado).
      final contratoId = ref.read(contratoAtualProvider);
      await ref
          .read(promocoesRepositoryProvider)
          .registrarInteresse(p.id, contratoId: contratoId);
      if (!mounted) return;
      setState(() => _cta = _CtaState.done);
      // Invalida o cache do detalhe para que o próximo GET retorne
      // interesseRegistrado=true. O _cta local segura o visual "done"
      // durante o refetch, então não há flash de botão idle.
      ref.invalidate(promocaoDetalheProvider(p.id));
    } catch (_) {
      if (!mounted) return;
      setState(() => _cta = _CtaState.idle);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não conseguimos registrar agora. Tenta de novo?'),
        ),
      );
    }
  }
}

class _Conteudo extends StatelessWidget {
  const _Conteudo({
    required this.promo,
    required this.cta,
    required this.onCta,
  });

  final PromocaoDetalheDto promo;
  final _CtaState cta;
  final VoidCallback onCta;

  @override
  Widget build(BuildContext context) {
    final from = hexColor(promo.gradientFrom) ?? BrandTokens.promoFallbackFrom;
    final to = hexColor(promo.gradientTo) ?? BrandTokens.promoFallbackTo;
    final imagemUrl = promo.imagemUrl;
    final imagemAbs = imagemUrl == null
        ? null
        : (imagemUrl.startsWith('http') ? imagemUrl : '$apiBaseUrl$imagemUrl');
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;

    return Stack(
      children: [
        CustomScrollView(
          slivers: [
            SliverAppBar(
              expandedHeight: 240,
              pinned: true,
              backgroundColor: from,
              foregroundColor: Colors.white,
              flexibleSpace: FlexibleSpaceBar(
                background: Hero(
                  tag: 'promo-${promo.id}',
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [from, to],
                      ),
                      image: imagemAbs == null
                          ? null
                          : DecorationImage(
                              image: NetworkImage(imagemAbs),
                              fit: BoxFit.cover,
                              opacity: 0.35,
                            ),
                    ),
                    child: Center(
                      child: Container(
                        width: 88,
                        height: 88,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          promoIconOf(promo.icon),
                          color: Colors.white,
                          size: 42,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            SliverPadding(
              padding: EdgeInsets.fromLTRB(
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                BrandTokens.spaceLg,
                // espaço pro botão fixo não cobrir o fim do conteúdo
                120 + MediaQuery.paddingOf(context).bottom,
              ),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  Text(
                    promo.titulo,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),
                  if (promo.subtitulo.isNotEmpty) ...[
                    const SizedBox(height: BrandTokens.spaceSm),
                    Text(
                      promo.subtitulo,
                      style: TextStyle(
                        fontSize: 15,
                        color: secondary,
                        height: 1.4,
                      ),
                    ),
                  ],
                  if ((promo.descricaoLonga ?? '').isNotEmpty) ...[
                    const SizedBox(height: BrandTokens.spaceLg),
                    Text(
                      promo.descricaoLonga!,
                      style: const TextStyle(fontSize: 15, height: 1.55),
                    ),
                  ],
                  if ((promo.regulamento ?? '').isNotEmpty ||
                      promo.validoAte != null) ...[
                    const SizedBox(height: BrandTokens.spaceLg),
                    _RegrasExpansivel(
                      regulamento: promo.regulamento,
                      validoAte: promo.validoAte,
                    ),
                  ],
                ]),
              ),
            ),
          ],
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: _CtaBar(promo: promo, cta: cta, onCta: onCta),
        ),
      ],
    );
  }
}

class _RegrasExpansivel extends StatelessWidget {
  const _RegrasExpansivel({required this.regulamento, required this.validoAte});
  final String? regulamento;
  final DateTime? validoAte;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;
    return Container(
      decoration: BoxDecoration(
        color: BrandTokens.primary.withValues(alpha: isDark ? 0.08 : 0.05),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          title: const Text(
            'Regras da promoção',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            BrandTokens.spaceMd, 0, BrandTokens.spaceMd, BrandTokens.spaceMd,
          ),
          children: [
            if ((regulamento ?? '').isNotEmpty)
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  regulamento!,
                  style: TextStyle(fontSize: 13, height: 1.5, color: secondary),
                ),
              ),
            if (validoAte != null) ...[
              const SizedBox(height: BrandTokens.spaceSm),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Válida até ${DateFormat('dd/MM/yyyy').format(validoAte!.toLocal())}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: secondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CtaBar extends StatelessWidget {
  const _CtaBar({required this.promo, required this.cta, required this.onCta});
  final PromocaoDetalheDto promo;
  final _CtaState cta;
  final VoidCallback onCta;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? BrandTokens.surfaceDark : BrandTokens.surface;
    final temAcaoPropria =
        promo.ctaAction.startsWith('tela:') || promo.ctaAction.startsWith('url:');
    final label = temAcaoPropria
        ? promo.ctaLabel
        : switch (cta) {
            _CtaState.idle => 'Tenho interesse',
            _CtaState.sending => 'Enviando…',
            _CtaState.done => '✓ Recebemos! Logo entramos em contato',
          };
    final done = cta == _CtaState.done && !temAcaoPropria;

    return Container(
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceMd + MediaQuery.paddingOf(context).bottom,
      ),
      decoration: BoxDecoration(
        color: bg.withValues(alpha: 0.92),
        border: Border(
          top: BorderSide(
            color: isDark
                ? Colors.white.withValues(alpha: 0.06)
                : BrandTokens.divider,
          ),
        ),
      ),
      child: FilledButton(
        onPressed: done || cta == _CtaState.sending ? null : onCta,
        style: done
            ? FilledButton.styleFrom(
                disabledBackgroundColor:
                    BrandTokens.success.withValues(alpha: 0.15),
                disabledForegroundColor: BrandTokens.accentDark,
              )
            : null,
        child: Text(label),
      ),
    );
  }
}
