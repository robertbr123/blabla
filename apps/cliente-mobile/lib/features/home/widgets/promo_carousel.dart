import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dto.dart';
import '../../../core/api/promocoes_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../promocoes/widgets/promo_card.dart';

/// Carrossel horizontal de promoções na home, consumindo a API real.
/// - Registra evento "view" 1,5s depois da página ficar visível (por card).
/// - No tap, registra evento "click" e navega para a landing /promocoes/:id.
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
      // Home coberta por outra rota → não avança nem registra view falsa.
      final route = ModalRoute.of(context);
      if (route != null && !route.isCurrent) return;
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
    ref.read(promocoesRepositoryProvider).registrarEvento(p.id, 'click');
    if (!mounted) return;
    context.push('/promocoes/${p.id}');
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
                child: PromoCard(item: widget.items[i], onTap: _onTap),
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

