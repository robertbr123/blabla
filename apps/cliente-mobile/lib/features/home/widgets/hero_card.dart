import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';
import 'connection_status_pill.dart';

/// Hero compacto da Home — segue padrao dos cards do Perfil/Faturas
/// (background da surface, sombra leve, sem gradient cheio).
/// Layout: avatar circular + saudacao/nome em coluna + status pill.
class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: isDark ? Colors.white12 : BrandTokens.divider,
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Row(
        children: [
          _Avatar(nome: me.nome),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _saudacaoComNome(me.nome),
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 15,
                    letterSpacing: -0.2,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    const Icon(
                      Icons.wifi_rounded,
                      size: 13,
                      color: BrandTokens.primary,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        me.planoNome ?? 'Sem plano vinculado',
                        style: const TextStyle(
                          color: BrandTokens.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: BrandTokens.spaceSm),
          const ConnectionStatusPill(),
        ],
      ),
    );
  }

  String _saudacaoComNome(String full) {
    final hora = DateTime.now().hour;
    final cumprimento = hora < 12
        ? 'Bom dia'
        : hora < 18
            ? 'Boa tarde'
            : 'Boa noite';
    final t = full.trim();
    final nome = t.isEmpty ? 'Cliente' : t.split(' ').first;
    return '$cumprimento, $nome';
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.nome});
  final String nome;

  String _iniciais() {
    final t = nome.trim();
    if (t.isEmpty) return '?';
    final parts = t.split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: BrandTokens.gradientHero,
        boxShadow: BrandTokens.shadowColored,
      ),
      alignment: Alignment.center,
      child: Text(
        _iniciais(),
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          fontSize: 16,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}
