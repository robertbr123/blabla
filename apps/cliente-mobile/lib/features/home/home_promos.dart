import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'widgets/promo_carousel.dart';

/// Placeholder de promoções até o bloco C (API real) ficar pronto.
/// Mantemos a interface de Provider pra trocar por FutureProvider que
/// consome `/api/cliente-app/promocoes` sem mexer na home.
final promocoesProvider = Provider<List<PromoItem>>((ref) {
  return const [
    PromoItem(
      titulo: 'Upgrade pra 1 Giga',
      subtitulo: 'Velocidade dobrada com o mesmo valor no primeiro mes.',
      ctaLabel: 'Quero esse',
      icon: Icons.rocket_launch_rounded,
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF8B5CF6), Color(0xFF5B6CFF)],
      ),
    ),
    PromoItem(
      titulo: 'Indique e ganhe',
      subtitulo: 'R\$30 de desconto na sua proxima fatura por indicacao.',
      ctaLabel: 'Indicar agora',
      icon: Icons.card_giftcard_rounded,
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFFE0455A), Color(0xFFE8A33D)],
      ),
    ),
    PromoItem(
      titulo: 'App de seguranca gratis',
      subtitulo: 'Antivirus pro celular incluso pra clientes Ondeline.',
      ctaLabel: 'Ativar',
      icon: Icons.shield_rounded,
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF14B8B0), Color(0xFF0F8F89)],
      ),
    ),
  ];
});
