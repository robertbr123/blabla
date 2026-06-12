import 'package:flutter/material.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/hex_color.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../home/promo_icon_map.dart';

/// Card de promoção compartilhado entre o carrossel da home e a página
/// /promocoes. Envolto em Hero(tag: 'promo-<id>') para animar a transição
/// até a landing de detalhe.
class PromoCard extends StatelessWidget {
  const PromoCard({super.key, required this.item, required this.onTap});

  final PromocaoDto item;
  final ValueChanged<PromocaoDto> onTap;

  @override
  Widget build(BuildContext context) {
    final from = hexColor(item.gradientFrom) ?? BrandTokens.promoFallbackFrom;
    final to = hexColor(item.gradientTo) ?? BrandTokens.promoFallbackTo;
    final imagemUrl = item.imagemUrl;
    final imagemAbs = imagemUrl == null
        ? null
        : (imagemUrl.startsWith('http') ? imagemUrl : '$apiBaseUrl$imagemUrl');

    return PressableScale(
      onTap: () => onTap(item),
      child: Hero(
        tag: 'promo-${item.id}',
        // Material(transparency) evita yellow underline nos Text dentro do
        // Hero durante o flight (Hero precisa de Material ancestor).
        child: Material(
          type: MaterialType.transparency,
          child: Container(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [from, to],
              ),
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              boxShadow: BrandTokens.elevation2,
              image: imagemAbs == null
                  ? null
                  : DecorationImage(
                      image: NetworkImage(imagemAbs),
                      fit: BoxFit.cover,
                      opacity: 0.35,
                    ),
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
                      if (item.subtitulo.isNotEmpty) ...[
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
                      ],
                      const SizedBox(height: BrandTokens.spaceSm),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: BrandTokens.spaceMd,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          borderRadius:
                              BorderRadius.circular(BrandTokens.radiusSm),
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.30),
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
                const SizedBox(width: BrandTokens.spaceMd),
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.18),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(promoIconOf(item.icon), color: Colors.white, size: 30),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
