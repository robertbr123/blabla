import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/manutencoes_repository.dart';
import '../../../core/branding/brand_tokens.dart';

/// Faixa "breaking news" que aparece no topo da Home quando ha manutencoes
/// ativas pra cidade do cliente.
///
/// - Texto rola horizontalmente em loop (marquee).
/// - Cor vermelho-laranja chamando atencao sem ser agressiva demais.
/// - Auto-esconde quando nao ha manutencao ativa.
class ManutencaoBreakingBar extends ConsumerWidget {
  const ManutencaoBreakingBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(manutencoesAtivasProvider);
    return async.when(
      data: (list) {
        if (list.isEmpty) return const SizedBox.shrink();
        return _MarqueeBar(items: list);
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}

class _MarqueeBar extends StatefulWidget {
  const _MarqueeBar({required this.items});
  final List<ManutencaoBreakingDto> items;

  @override
  State<_MarqueeBar> createState() => _MarqueeBarState();
}

class _MarqueeBarState extends State<_MarqueeBar>
    with SingleTickerProviderStateMixin {
  late final ScrollController _ctrl;
  late final AnimationController _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = ScrollController();
    // Velocidade ~30px/segundo, loop infinito.
    _anim = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 30),
    )..repeat();
    _anim.addListener(_tick);
  }

  void _tick() {
    if (!_ctrl.hasClients) return;
    final max = _ctrl.position.maxScrollExtent;
    if (max <= 0) return;
    // Posicao baseada no progresso da animacao — loop continuo.
    final target = _anim.value * max;
    _ctrl.jumpTo(target);
  }

  @override
  void dispose() {
    _anim.removeListener(_tick);
    _anim.dispose();
    _ctrl.dispose();
    super.dispose();
  }

  String _textoCompleto() {
    final partes = widget.items.map((m) {
      final desc = (m.descricao ?? '').trim();
      return desc.isEmpty ? m.titulo : '${m.titulo} — $desc';
    }).toList();
    // Duplica pra dar sensacao de loop continuo.
    final base = partes.join('   ●   ');
    return '$base   ●   $base';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      padding: const EdgeInsets.symmetric(
        horizontal: BrandTokens.spaceMd,
        vertical: 10,
      ),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [BrandTokens.danger, BrandTokens.dangerStrong],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        boxShadow: [
          BoxShadow(
            color: BrandTokens.danger.withOpacity(0.30),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceSm,
              vertical: 3,
            ),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  color: BrandTokens.dangerStrong,
                  size: 13,
                ),
                SizedBox(width: 4),
                Text(
                  'AVISO',
                  style: TextStyle(
                    color: BrandTokens.dangerStrong,
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: BrandTokens.spaceSm),
          Expanded(
            child: ShaderMask(
              shaderCallback: (rect) {
                return LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: const [
                    Colors.transparent,
                    Colors.white,
                    Colors.white,
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.04, 0.96, 1.0],
                ).createShader(rect);
              },
              blendMode: BlendMode.dstIn,
              child: SingleChildScrollView(
                controller: _ctrl,
                scrollDirection: Axis.horizontal,
                physics: const NeverScrollableScrollPhysics(),
                child: Text(
                  _textoCompleto(),
                  maxLines: 1,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
