import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/dto.dart';
import '../../../core/api/promocoes_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/hex_color.dart';
import '../../../core/ui/pressable_scale.dart';
import '../promo_icon_map.dart';

/// Carrossel horizontal de promocoes na home, consumindo a API real.
/// - Registra evento "view" 1.5s depois da pagina ficar visivel.
/// - Registra evento "click" no tap do CTA.
/// - CTA: "info" no-op, "url:<https>" abre browser, "tela:<rota>" navega in-app.
class PromoCarousel extends ConsumerStatefulWidget {
  const PromoCarousel({super.key, required this.items});
  final List<PromocaoDto> items;

  @override
  ConsumerState<PromoCarousel> createState() => _PromoCarouselState();
}

class _PromoCarouselState extends ConsumerState<PromoCarousel> {
  final PageController _ctrl = PageController(viewportFraction: 0.92);
  int _idx = 0;
  final Set<String> _viewedIds = {};
  Timer? _viewTimer;
  Timer? _autoTimer;
  Timer? _resumeTimer;

  @override
  void initState() {
    super.initState();
    _scheduleView(0);
    _startAuto();
  }

  @override
  void didUpdateWidget(covariant PromoCarousel old) {
    super.didUpdateWidget(old);
    // Lista mudou de tamanho (ex: refresh trouxe mais promos) → re-liga/desliga
    // o auto-scroll conforme o caso.
    if (old.items.length != widget.items.length) {
      _startAuto();
    }
  }

  @override
  void dispose() {
    _autoTimer?.cancel();
    _resumeTimer?.cancel();
    _viewTimer?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  void _startAuto() {
    _autoTimer?.cancel();
    if (widget.items.length < 2) return;
    _autoTimer = Timer.periodic(const Duration(seconds: 6), (_) {
      if (!mounted || !_ctrl.hasClients) return;
      final next = (_idx + 1) % widget.items.length;
      _ctrl.animateToPage(
        next,
        duration: const Duration(milliseconds: 480),
        curve: const Cubic(0.32, 0.72, 0, 1),
      );
    });
  }

  // Usuário tocou: pausa o auto-scroll e retoma após 10s de inatividade.
  void _pauseAuto() {
    _autoTimer?.cancel();
    _resumeTimer?.cancel();
    _resumeTimer = Timer(const Duration(seconds: 10), () {
      if (mounted) _startAuto();
    });
  }

  void _scheduleView(int idx) {
    _viewTimer?.cancel();
    if (idx < 0 || idx >= widget.items.length) return;
    final id = widget.items[idx].id;
    if (_viewedIds.contains(id)) return;
    _viewTimer = Timer(const Duration(milliseconds: 1500), () {
      if (!mounted) return;
      _viewedIds.add(id);
      ref.read(promocoesRepositoryProvider).registrarEvento(id, 'view');
    });
  }

  Future<void> _onTap(PromocaoDto p) async {
    // Click sempre registra
    ref.read(promocoesRepositoryProvider).registrarEvento(p.id, 'click');

    final action = p.ctaAction;
    if (action == 'info') return;
    if (action.startsWith('url:')) {
      final url = action.substring(4);
      final uri = Uri.tryParse(url);
      if (uri != null) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
      return;
    }
    if (action.startsWith('tela:')) {
      final rota = action.substring(5);
      if (!mounted) return;
      // ignore: use_build_context_synchronously
      context.push(rota);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();
    return Column(
      children: [
        SizedBox(
          height: 172,
          child: Listener(
            onPointerDown: (_) => _pauseAuto(),
            child: PageView.builder(
              controller: _ctrl,
              onPageChanged: (i) {
                setState(() => _idx = i);
                _scheduleView(i);
              },
              itemCount: widget.items.length,
              itemBuilder: (_, i) => Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: _PromoCard(item: widget.items[i], onTap: _onTap),
              ),
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
  const _PromoCard({required this.item, required this.onTap});
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
              const SizedBox(width: BrandTokens.spaceMd),
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.18),
                  shape: BoxShape.circle,
                ),
                child: Icon(promoIconOf(item.icon), color: Colors.white, size: 30),
              ),
            ],
          ),
        ),
    );
  }
}
