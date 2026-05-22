import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';
import 'connection_status_pill.dart';

class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: Stack(
        children: [
          // Decoração geométrica de fundo
          Positioned(
            right: -40,
            top: -40,
            child: IgnorePointer(
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withOpacity(0.06),
                ),
              ),
            ),
          ),
          Positioned(
            right: -80,
            bottom: -80,
            child: IgnorePointer(
              child: Container(
                width: 200,
                height: 200,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withOpacity(0.04),
                ),
              ),
            ),
          ),
          // Gradient + conteúdo
          Container(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            decoration: BoxDecoration(
              gradient: BrandTokens.gradientHero,
              boxShadow: BrandTokens.elevation2,
            ),
            child: _Content(me: me),
          ),
        ],
      ),
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            _Avatar(nome: me.nome),
            const SizedBox(width: BrandTokens.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _saudacao(),
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _primeiroNome(me.nome),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const ConnectionStatusPill(),
          ],
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceMd,
            vertical: BrandTokens.spaceMd,
          ),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.12),
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
            border: Border.all(color: Colors.white.withOpacity(0.16)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: const Icon(
                  Icons.wifi_rounded,
                  color: Colors.white,
                  size: 20,
                ),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Seu plano',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      me.planoNome ?? 'Sem plano vinculado',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _saudacao() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Bom dia,';
    if (h < 18) return 'Boa tarde,';
    return 'Boa noite,';
  }

  String _primeiroNome(String full) {
    final t = full.trim();
    if (t.isEmpty) return 'Cliente';
    return t.split(' ').first;
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
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            Colors.white.withOpacity(0.30),
            Colors.white.withOpacity(0.10),
          ],
        ),
        border: Border.all(color: Colors.white.withOpacity(0.35), width: 1.5),
      ),
      alignment: Alignment.center,
      child: Text(
        _iniciais(),
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          fontSize: 16,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
