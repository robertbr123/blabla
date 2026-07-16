import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/capa_folha.dart';
import '../../../core/ui/formatters.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../notificacoes/widgets/notif_bell.dart';
import 'connection_status_pill.dart';

/// Header colapsável e fixo (pinned) da home: capa ciano com saudação + sino
/// + bloco de status integrado (conexão, plano, aparelhos, atalho "Minha
/// rede") + linha de endereço/troca de contrato. Ao rolar, saudação/sino/
/// linha de contrato somem (fade) e o bloco de status vira uma faixa
/// compacta única, sempre fixa no topo — igual ao padrão do PerfilScreen
/// (`_PerfilCapaDelegate`).
class HomeCapaDelegate extends SliverPersistentHeaderDelegate {
  const HomeCapaDelegate({
    required this.topInset,
    this.fontScale = 1.0,
    this.me,
    this.rede,
    this.contratoAtual,
    this.podeTrocarContrato = false,
    this.onTrocarContrato,
    this.loading = false,
    this.errorMode = false,
    this.onRetry,
  });

  final double topInset;

  /// Fator de escala de fonte já limitado a no máximo 1.2x (ver
  /// `MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.2)` no
  /// screen que instancia este delegate). Em 1.0 (default) o layout é
  /// idêntico ao original — usado pra escalar os offsets/extents fixos
  /// do header proporcionalmente à fonte do sistema, evitando que texto
  /// grande seja cortado pelo ClipRect.
  final double fontScale;
  final MeDto? me;
  final RedeAparelhosDto? rede;
  final ContratoResumoDto? contratoAtual;
  final bool podeTrocarContrato;
  final void Function(BuildContext context)? onTrocarContrato;
  final bool loading;
  final bool errorMode;
  final VoidCallback? onRetry;

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  /// Altura extra (além do topInset) do header totalmente expandido:
  /// saudação+sino, bloco de status completo (com linha de aparelhos) e
  /// linha de contrato, cabem confortavelmente nessa faixa.
  static const double expandedExtra = 230;

  /// Altura extra (além do topInset) do header totalmente colapsado:
  /// faixa compacta de status (uma linha) + lábio da folha.
  static const double collapsedExtra = 92;

  @override
  double get maxExtent => topInset + expandedExtra * fontScale;

  @override
  double get minExtent => topInset + collapsedExtra * fontScale;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    final range = maxExtent - minExtent;
    final t = range <= 0 ? 0.0 : (shrinkOffset / range).clamp(0.0, 1.0);
    // Faixa útil colapsada (acima do lábio da folha), já escalada pra
    // fonte grande caber sem cortar.
    final collapsedBand =
        collapsedExtra * fontScale - BrandTokens.radiusFolha;

    Widget content;
    if (loading) {
      content = const Padding(
        padding: EdgeInsets.only(bottom: BrandTokens.radiusFolha),
        child: Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
      );
    } else if (errorMode) {
      content = Padding(
        padding: EdgeInsets.fromLTRB(
          BrandTokens.spaceLg,
          _lerp(
            topInset + (BrandTokens.spaceLg + 24) * fontScale,
            topInset + (collapsedBand - 22 * fontScale) / 2,
            t,
          ),
          BrandTokens.spaceLg,
          0,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Opacity(
              opacity: (1 - t * 2).clamp(0.0, 1.0),
              child: const Icon(Icons.error_outline, color: Colors.white),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            Text(
              'Não conseguimos carregar seus dados.',
              style: TextStyle(color: Colors.white, fontSize: _lerp(15, 13, t)),
            ),
            if (onRetry != null)
              TextButton(
                onPressed: onRetry,
                style: TextButton.styleFrom(
                  padding: EdgeInsets.zero,
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: const Text(
                  'Tentar de novo',
                  style: TextStyle(color: Colors.white),
                ),
              ),
          ],
        ),
      );
    } else {
      content = _ExpandedCollapsedContent(
        t: t,
        topInset: topInset,
        fontScale: fontScale,
        collapsedBand: collapsedBand,
        me: me,
        rede: rede,
        contratoAtual: contratoAtual,
        podeTrocarContrato: podeTrocarContrato,
        onTrocarContrato: onTrocarContrato,
      );
    }

    // Clampa a fonte do sistema a no máximo 1.2x dentro do header: acima
    // disso os offsets/extents (já escalados por `fontScale`, o mesmo
    // fator) deixam de garantir espaço suficiente e o texto voltaria a
    // ser cortado pelo ClipRect abaixo.
    content = MediaQuery.withClampedTextScaling(
      maxScaleFactor: 1.2,
      child: content,
    );

    // Lábio da folha pintado por cima do gradiente, dentro do próprio
    // header — mesmo padrão do PerfilScreen: capa e canto arredondado
    // vivem no mesmo box e nunca deixam fresta em nenhum shrinkOffset.
    return ClipRect(
      child: SizedBox.expand(
        child: Stack(
          fit: StackFit.expand,
          children: [
            CapaBackground(padding: EdgeInsets.zero, child: content),
            const Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: FolhaLip(),
            ),
          ],
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(covariant HomeCapaDelegate oldDelegate) {
    return oldDelegate.topInset != topInset ||
        oldDelegate.fontScale != fontScale ||
        oldDelegate.me != me ||
        oldDelegate.rede != rede ||
        oldDelegate.contratoAtual != contratoAtual ||
        oldDelegate.podeTrocarContrato != podeTrocarContrato ||
        oldDelegate.loading != loading ||
        oldDelegate.errorMode != errorMode;
  }
}

/// Conteúdo real do header (estado com dados), interpolado por `t`.
class _ExpandedCollapsedContent extends StatelessWidget {
  const _ExpandedCollapsedContent({
    required this.t,
    required this.topInset,
    required this.fontScale,
    required this.collapsedBand,
    required this.me,
    required this.rede,
    required this.contratoAtual,
    required this.podeTrocarContrato,
    required this.onTrocarContrato,
  });

  final double t;
  final double topInset;
  final double fontScale;
  final double collapsedBand;
  final MeDto? me;
  final RedeAparelhosDto? rede;
  final ContratoResumoDto? contratoAtual;
  final bool podeTrocarContrato;
  final void Function(BuildContext context)? onTrocarContrato;

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  String _primeiroNome(String full) {
    final t = full.trim();
    if (t.isEmpty) return 'Cliente';
    final p = t.split(RegExp(r'\s+')).first;
    if (p.isEmpty) return 'Cliente';
    return p[0].toUpperCase() + p.substring(1).toLowerCase();
  }

  @override
  Widget build(BuildContext context) {
    final nome = me == null ? 'Cliente' : _primeiroNome(me!.nome);
    final planoNome = me?.planoNome ?? 'Sem plano vinculado';

    // Fade rápido: saudação, sino e linha de contrato somem já no início
    // do colapso (por volta de 40-25% do scroll) — quando o bloco de
    // status já assumiu a posição fixa deles.
    final greetingOpacity = (1 - t * 2.5).clamp(0.0, 1.0);
    final contratoOpacity = (1 - t * 4).clamp(0.0, 1.0);

    // Faixa útil do estado colapsado (acima do lábio da folha): minExtent
    // (92) menos o lábio da folha (radiusFolha=28) = 64 — escalada em
    // `collapsedBand` (calculado pelo delegate) pra caber fonte grande.
    final expandedStatusTop = topInset +
        (BrandTokens.spaceMd + 46 + BrandTokens.spaceMd) * fontScale;
    final collapsedStatusTop = topInset + (collapsedBand - 40 * fontScale) / 2;
    final statusTop = _lerp(expandedStatusTop, collapsedStatusTop, t);

    return Stack(
      children: [
        // Saudação + nome
        Positioned(
          left: BrandTokens.spaceLg,
          right: BrandTokens.spaceLg + 48,
          top: topInset + BrandTokens.spaceMd * fontScale,
          child: Opacity(
            opacity: greetingOpacity,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  saudacao(DateTime.now()),
                  style: TextStyle(
                    color: BrandTokens.capaInk.withValues(alpha: 0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '$nome 👋',
                  style: BrandTokens.displayGreeting,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
        // Sino de notificações
        Positioned(
          right: BrandTokens.spaceLg - 12,
          top: topInset + (BrandTokens.spaceMd - 8) * fontScale,
          child: Opacity(
            opacity: greetingOpacity,
            child: const NotifBell(color: BrandTokens.capaInk),
          ),
        ),
        // Bloco de status (conexão + plano + aparelhos + atalho rede)
        Positioned(
          left: BrandTokens.spaceLg,
          right: BrandTokens.spaceLg,
          top: statusTop,
          child: _StatusBlock(t: t, planoNome: planoNome, rede: rede),
        ),
        // Linha de endereço / troca de contrato
        if (contratoAtual != null && contratoAtual!.enderecoResumido.isNotEmpty)
          Positioned(
            left: BrandTokens.spaceLg,
            right: BrandTokens.spaceLg,
            top: expandedStatusTop + (BrandTokens.spaceSm + 78) * fontScale,
            child: Opacity(
              opacity: contratoOpacity,
              child: _ContratoLinha(
                contrato: contratoAtual!,
                podeTrocar: podeTrocarContrato,
                onTrocar: onTrocarContrato == null
                    ? null
                    : () => onTrocarContrato!(context),
              ),
            ),
          ),
      ],
    );
  }
}

/// Bloco translúcido com status da conexão + plano + linha de rede.
/// Em `t=0` é idêntico ao bloco original da home; conforme `t` cresce, a
/// linha de aparelhos encolhe (Align heightFactor) e um chip "Minha rede →"
/// aparece dentro da própria linha do status (largura/opacidade animadas),
/// formando a faixa compacta de uma linha só quando totalmente colapsado.
class _StatusBlock extends StatelessWidget {
  const _StatusBlock({required this.t, required this.planoNome, required this.rede});

  final double t;
  final String planoNome;
  final RedeAparelhosDto? rede;

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  String _saudeLabel(String saude) => switch (saude) {
        'excelente' => 'Ótimo',
        'boa' => 'Bom',
        'fraca' => 'Fraco',
        _ => 'Ativo',
      };

  @override
  Widget build(BuildContext context) {
    final rede = this.rede;
    return Container(
      padding: EdgeInsets.all(_lerp(16, 10, t)),
      decoration: BoxDecoration(
        color: BrandTokens.capaInk.withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const ConnectionStatusPill(),
              const SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  planoNome,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              // Chip compacto "Minha rede →": sem largura/opacidade em
              // t=0 (idêntico a hoje), cresce conforme colapsa — visível
              // mesmo quando a rede não foi encontrada (é só atalho de
              // navegação).
              ClipRect(
                child: SizedBox(
                  width: _lerp(0, 108, t),
                  child: Opacity(
                    opacity: t,
                    child: const Align(
                      alignment: Alignment.centerRight,
                      child: _MinhaRedeChip(),
                    ),
                  ),
                ),
              ),
            ],
          ),
          if (rede != null)
            Align(
              alignment: Alignment.topLeft,
              heightFactor: (1 - t).clamp(0.0, 1.0),
              child: ClipRect(
                child: Padding(
                  padding: const EdgeInsets.only(top: BrandTokens.spaceSm),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          '📱 ${rede.aparelhos.length} '
                          '${rede.aparelhos.length == 1 ? "aparelho" : "aparelhos"}'
                          ' · sinal ${_saudeLabel(rede.saude)}',
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.85),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const _MinhaRedeChip(),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _MinhaRedeChip extends StatelessWidget {
  const _MinhaRedeChip();

  @override
  Widget build(BuildContext context) {
    return PressableScale(
      onTap: () => context.push('/rede'),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceSm + 2,
          vertical: 5,
        ),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.22),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Text(
          'Minha rede →',
          style: TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.w800,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}

/// Linha de endereço do contrato na capa; clicável quando multi-contrato.
class _ContratoLinha extends StatelessWidget {
  const _ContratoLinha({
    required this.contrato,
    required this.podeTrocar,
    required this.onTrocar,
  });
  final ContratoResumoDto contrato;
  final bool podeTrocar;
  final VoidCallback? onTrocar;

  @override
  Widget build(BuildContext context) {
    final linha = Row(
      children: [
        Icon(Icons.location_on_outlined,
            size: 14, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            contrato.enderecoResumido,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: BrandTokens.capaInk.withValues(alpha: 0.7),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (podeTrocar)
          Icon(Icons.swap_horiz_rounded,
              size: 16, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
      ],
    );
    if (!podeTrocar || onTrocar == null) return linha;
    return GestureDetector(onTap: onTrocar, child: linha);
  }
}
