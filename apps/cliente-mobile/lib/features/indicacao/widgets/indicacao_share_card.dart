import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

/// Card visual usado tanto pra preview quanto pra gerar imagem PNG
/// compartilhavel (status do WhatsApp).
///
/// Tamanho fixo (1080x1920 logical scale-down) — funciona bem como
/// imagem 9:16 pro status.
class IndicacaoShareCard extends StatelessWidget {
  const IndicacaoShareCard({
    super.key,
    required this.codigo,
    this.nomeEmpresa = 'Ondeline',
    this.recompensa = '1 mês grátis',
  });

  final String codigo;
  final String nomeEmpresa;
  final String recompensa;

  static const Size designSize = Size(540, 960); // 9:16 — boa pra status

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: designSize.width,
      height: designSize.height,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Fundo gradient
          DecoratedBox(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF0B1F3A),
                  Color(0xFF14B8B0),
                ],
              ),
            ),
          ),
          // Bolhas decorativas
          Positioned(
            top: -60,
            right: -40,
            child: _Blob(
              size: 220,
              color: Colors.white.withOpacity(0.07),
            ),
          ),
          Positioned(
            bottom: -80,
            left: -60,
            child: _Blob(
              size: 260,
              color: Colors.white.withOpacity(0.05),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 36,
              vertical: 64,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Logo/nome
                Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      alignment: Alignment.center,
                      child: const Text(
                        'O',
                        style: TextStyle(
                          fontWeight: FontWeight.w900,
                          color: BrandTokens.primaryDark,
                          fontSize: 22,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      nomeEmpresa,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 20,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 56),
                // Chamada
                const Text(
                  'Internet boa,\nbarato pra todo mundo.',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 38,
                    fontWeight: FontWeight.w900,
                    height: 1.1,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  'Use meu código quando contratar — você ganha desconto e eu também 🚀',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.92),
                    fontSize: 17,
                    fontWeight: FontWeight.w500,
                    height: 1.35,
                  ),
                ),
                const Spacer(),
                // Bloco do código
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 28,
                    vertical: 24,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.18),
                        blurRadius: 30,
                        offset: const Offset(0, 12),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'CÓDIGO',
                        style: TextStyle(
                          color: BrandTokens.textSecondary,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                          letterSpacing: 1.5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        codigo,
                        style: const TextStyle(
                          color: BrandTokens.primaryDark,
                          fontSize: 44,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 6,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                // Footer
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.card_giftcard_rounded,
                            color: Colors.white,
                            size: 16,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            recompensa,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Blob extends StatelessWidget {
  const _Blob({required this.size, required this.color});
  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }
}
