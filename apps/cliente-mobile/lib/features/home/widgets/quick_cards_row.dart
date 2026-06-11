import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/contatos_repository.dart';
import '../../../core/api/dto.dart';
import '../../../core/api/fidelidade_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/haptics.dart';
import '../../../core/ui/pressable_scale.dart';

/// Linha com 2 mini-cards lado a lado:
/// [Fidelidade — pontos] [Fale conosco — WhatsApp 24h]
///
/// Ambos sao auto-hide friendly: o de fidelidade so esconde se erro;
/// o de fale conosco esconde se nao houver WhatsApp configurado.
class QuickCardsRow extends ConsumerWidget {
  const QuickCardsRow({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: const [
            Expanded(child: _FidelidadeMiniCard()),
            SizedBox(width: BrandTokens.spaceSm),
            Expanded(child: _FaleConoscoMiniCard()),
          ],
        ),
      ),
    );
  }
}

// ════════ Fidelidade ════════

class _FidelidadeMiniCard extends ConsumerWidget {
  const _FidelidadeMiniCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(fidelidadeProvider);
    return PressableScale(
      onTap: () => context.push('/fidelidade'),
      child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [BrandTokens.warning, BrandTokens.accentOrange],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: [
              BoxShadow(
                color: BrandTokens.warning.withOpacity(0.25),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Row(
                children: [
                  Icon(
                    Icons.workspace_premium_rounded,
                    color: Colors.white,
                    size: 18,
                  ),
                  SizedBox(width: 6),
                  Text(
                    'Fidelidade',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              async.when(
                data: (d) => Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      '${d.pontosDisponiveis}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.8,
                      ),
                    ),
                    const SizedBox(width: 3),
                    const Text(
                      'pts',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                loading: () => const SizedBox(
                  height: 26,
                  width: 26,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(Colors.white),
                  ),
                ),
                error: (_, __) => const Text(
                  '—',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 26,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(height: 2),
              const Text(
                'Trocar pontos →',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
    );
  }
}

// ════════ Fale conosco ════════

class _FaleConoscoMiniCard extends ConsumerWidget {
  const _FaleConoscoMiniCard();

  Future<void> _abrirWhats(BuildContext context, ContatoOperadoraDto whats) async {
    await Haptics.light();
    final num = whats.valor.replaceAll(RegExp(r'\D'), '');
    if (num.isEmpty) {
      if (context.mounted) context.push('/contatos');
      return;
    }
    final uri = Uri.parse('https://wa.me/$num');
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Object {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não consegui abrir o WhatsApp.')),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(contatosOperadoraProvider);
    ContatoOperadoraDto? whats;
    String subtitle = 'WhatsApp 24h';
    async.whenData((list) {
      for (final c in list) {
        if (c.tipo == 'whatsapp') {
          whats = c;
          if (c.subtitle != null && c.subtitle!.isNotEmpty) {
            subtitle = c.subtitle!;
          }
          break;
        }
      }
    });

    return PressableScale(
      onTap: () {
        if (whats != null) {
          _abrirWhats(context, whats!);
        } else {
          context.push('/contatos');
        }
      },
      child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [BrandTokens.brandWhatsapp, BrandTokens.brandWhatsappDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: [
              BoxShadow(
                color: BrandTokens.brandWhatsapp.withOpacity(0.25),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Row(
                children: [
                  Icon(
                    Icons.chat_bubble_rounded,
                    color: Colors.white,
                    size: 18,
                  ),
                  SizedBox(width: 6),
                  Text(
                    'Fale conosco',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'WhatsApp',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                whats != null ? '$subtitle →' : 'Ver opções →',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
    );
  }
}
