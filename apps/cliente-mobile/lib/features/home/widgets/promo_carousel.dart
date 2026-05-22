import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

/// Item de promoção. Bloco C vai trocar pra DTO do backend.
class PromoItem {
  const PromoItem({
    required this.titulo,
    required this.subtitulo,
    required this.ctaLabel,
    this.onTap,
    this.gradient,
    this.icon,
  });
  final String titulo;
  final String subtitulo;
  final String ctaLabel;
  final VoidCallback? onTap;
  final LinearGradient? gradient;
  final IconData? icon;
}

/// Carrossel horizontal de promoções na home.
/// Por enquanto recebe lista in-memory; bloco C plugga API real
/// (`GET /api/cliente-app/promocoes`).
class PromoCarousel extends StatefulWidget {
  const PromoCarousel({super.key, required this.items});
  final List<PromoItem> items;

  @override
  State<PromoCarousel> createState() => _PromoCarouselState();
}

class _PromoCarouselState extends State<PromoCarousel> {
  final PageController _ctrl = PageController(viewportFraction: 0.92);
  int _idx = 0;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();
    return Column(
      children: [
        SizedBox(
          height: 140,
          child: PageView.builder(
            controller: _ctrl,
            onPageChanged: (i) => setState(() => _idx = i),
            itemCount: widget.items.length,
            itemBuilder: (_, i) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: _PromoCard(item: widget.items[i]),
            ),
          ),
        ),
        if (widget.items.length > 1) ...[
          const SizedBox(height: BrandTokens.spaceSm),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(widget.items.length, (i) {
              final active = i == _idx;
              return AnimatedContainer(
                duration: BrandTokens.motionMedium,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: active ? 18 : 6,
                height: 6,
                decoration: BoxDecoration(
                  color: active
                      ? BrandTokens.primary
                      : BrandTokens.primary.withOpacity(0.30),
                  borderRadius: BorderRadius.circular(3),
                ),
              );
            }),
          ),
        ],
      ],
    );
  }
}

class _PromoCard extends StatelessWidget {
  const _PromoCard({required this.item});
  final PromoItem item;

  @override
  Widget build(BuildContext context) {
    final gradient = item.gradient ??
        const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF8B5CF6), Color(0xFF5B6CFF)],
        );
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: item.onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          decoration: BoxDecoration(
            gradient: gradient,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: BrandTokens.elevation2,
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      item.titulo,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 17,
                        letterSpacing: -0.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.subtitulo,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: BrandTokens.spaceSm),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: BrandTokens.spaceMd,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.18),
                        borderRadius:
                            BorderRadius.circular(BrandTokens.radiusSm),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.30),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            item.ctaLabel,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_forward_rounded,
                            color: Colors.white,
                            size: 14,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              if (item.icon != null)
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.18),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(item.icon, color: Colors.white, size: 30),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
