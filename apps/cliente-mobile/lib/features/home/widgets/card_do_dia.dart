import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/card_dia_repository.dart';
import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/haptics.dart';
import '../../shell/main_shell.dart';
import '../promo_icon_map.dart';

/// Card rotativo "dica do dia" — backend escolhe 1 ativo por (user, data).
/// Auto-hide quando endpoint devolve null ou erro (graceful degrade).
class CardDoDia extends ConsumerWidget {
  const CardDoDia({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(cardDiaProvider);
    return async.maybeWhen(
      data: (card) {
        if (card == null) return const SizedBox.shrink();
        return _CardDoDiaContent(card: card);
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

class _CardDoDiaContent extends ConsumerWidget {
  const _CardDoDiaContent({required this.card});
  final CardDiaDto card;

  Color _parseHex(String? hex, Color fallback) {
    if (hex == null || hex.isEmpty) return fallback;
    final clean = hex.replaceAll('#', '');
    if (clean.length != 6 && clean.length != 8) return fallback;
    final v = int.tryParse(clean.length == 6 ? 'FF$clean' : clean, radix: 16);
    return v == null ? fallback : Color(v);
  }

  Future<void> _onTap(BuildContext context, WidgetRef ref) async {
    await Haptics.light();
    final action = card.ctaAction;
    if (action == 'info') return;
    if (action.startsWith('url:')) {
      final url = action.substring(4);
      final uri = Uri.tryParse(url);
      if (uri == null) return;
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      return;
    }
    if (action.startsWith('tela:')) {
      final rota = action.substring(5);
      // Atalhos pras tabs do MainShell — evita rota nova.
      switch (rota) {
        case '/home':
          ref.read(mainShellTabProvider.notifier).state = 0;
          return;
        case '/faturas':
          ref.read(mainShellTabProvider.notifier).state = 1;
          return;
        case '/suporte':
          ref.read(mainShellTabProvider.notifier).state = 2;
          return;
        case '/perfil':
          ref.read(mainShellTabProvider.notifier).state = 3;
          return;
        default:
          if (context.mounted) context.push(rota);
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final from = _parseHex(card.gradientFrom, BrandTokens.primary);
    final to = _parseHex(card.gradientTo, BrandTokens.primaryDark);
    final clickable = card.ctaAction != 'info';

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          onTap: clickable ? () => _onTap(context, ref) : null,
          child: Container(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [from, to],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              boxShadow: [
                BoxShadow(
                  color: from.withOpacity(0.25),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    promoIconOf(card.icon),
                    color: Colors.white,
                    size: 24,
                  ),
                ),
                const SizedBox(width: BrandTokens.spaceMd),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        card.titulo,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 16,
                          letterSpacing: -0.2,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        card.corpo,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.92),
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                          height: 1.35,
                        ),
                      ),
                      if (clickable) ...[
                        const SizedBox(height: BrandTokens.spaceSm),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              card.ctaLabel,
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(
                              Icons.arrow_forward_rounded,
                              color: Colors.white,
                              size: 16,
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
