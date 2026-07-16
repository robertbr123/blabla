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
/// rede") + linha de endereço/troca de contrato. Ao rolar, o layout
/// expandido (saudação/sino/bloco completo/linha de contrato) faz crossfade
/// pra um layout colapsado compacto (faixa de status de uma linha + linha
/// de contrato compacta), ambos sempre fixos no topo — igual ao padrão do
/// PerfilScreen (`_PerfilCapaDelegate`).
///
/// Implementação: dois layouts NATURAIS (Column/Padding, layout por flow) em
/// vez de posicionamento absoluto por elemento — cada layout é montado uma
/// vez e só a opacidade cruza entre eles, o que elimina os desalinhamentos
/// que o lerp de posição por elemento produzia.
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
  /// faixa compacta de status (uma linha) + linha compacta do contrato
  /// (endereço + troca) + lábio da folha. +20 sobre o valor original pra
  /// acomodar a linha de contrato sem colidir com o lip.
  static const double collapsedExtra = 112;

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
      content = _HeaderCrossfade(
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

/// Crossfade entre os dois layouts naturais (expandido/colapsado) do
/// conteúdo do header. Cada layout é montado inteiro e só a opacidade
/// cruza entre `t=0` (expandido) e `t=1` (colapsado) — nenhuma posição é
/// interpolada, então cada layout é sempre internamente consistente
/// (Column/Padding normais), o que elimina os desalinhamentos do esquema
/// anterior de `Positioned` por elemento com lerp de topo.
class _HeaderCrossfade extends StatelessWidget {
  const _HeaderCrossfade({
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

  String _primeiroNome(String full) {
    final s = full.trim();
    if (s.isEmpty) return 'Cliente';
    final p = s.split(RegExp(r'\s+')).first;
    if (p.isEmpty) return 'Cliente';
    return p[0].toUpperCase() + p.substring(1).toLowerCase();
  }

  @override
  Widget build(BuildContext context) {
    final nome = me == null ? 'Cliente' : _primeiroNome(me!.nome);
    final planoNome = me?.planoNome ?? 'Sem plano vinculado';
    final onTrocar =
        onTrocarContrato == null ? null : () => onTrocarContrato!(context);

    final expanded = _ExpandedLayout(
      topInset: topInset,
      fontScale: fontScale,
      nome: nome,
      planoNome: planoNome,
      rede: rede,
      contratoAtual: contratoAtual,
      podeTrocarContrato: podeTrocarContrato,
      onTrocar: onTrocar,
    );

    final collapsed = _CollapsedLayout(
      planoNome: planoNome,
      rede: rede,
      contratoAtual: contratoAtual,
      podeTrocarContrato: podeTrocarContrato,
      onTrocar: onTrocar,
    );

    return Stack(
      children: [
        // Layout expandido: preenche o topo do header e some (fade) por
        // volta da metade do colapso — quando o layout colapsado já
        // assumiu a faixa fixa no topo.
        Positioned(
          left: 0,
          right: 0,
          top: 0,
          child: IgnorePointer(
            ignoring: t > 0.5,
            child: Opacity(
              opacity: (1 - t * 2).clamp(0.0, 1.0),
              child: expanded,
            ),
          ),
        ),
        // Layout colapsado: faixa fixa logo abaixo do topInset, centrada
        // na banda útil acima do lábio da folha.
        Positioned(
          left: 0,
          right: 0,
          top: topInset,
          height: collapsedBand,
          child: IgnorePointer(
            ignoring: t <= 0.5,
            child: Opacity(
              opacity: ((t - 0.5) * 2).clamp(0.0, 1.0),
              child: collapsed,
            ),
          ),
        ),
      ],
    );
  }
}

/// Layout natural (por flow, sem `Positioned` por elemento) do estado
/// totalmente expandido: saudação + sino, bloco de status completo e linha
/// de contrato — o visual pré-colapso.
class _ExpandedLayout extends StatelessWidget {
  const _ExpandedLayout({
    required this.topInset,
    required this.fontScale,
    required this.nome,
    required this.planoNome,
    required this.rede,
    required this.contratoAtual,
    required this.podeTrocarContrato,
    required this.onTrocar,
  });

  final double topInset;
  final double fontScale;
  final String nome;
  final String planoNome;
  final RedeAparelhosDto? rede;
  final ContratoResumoDto? contratoAtual;
  final bool podeTrocarContrato;
  final VoidCallback? onTrocar;

  String _saudeLabel(String saude) => switch (saude) {
        'excelente' => 'Ótimo',
        'boa' => 'Bom',
        'fraca' => 'Fraco',
        _ => 'Ativo',
      };

  @override
  Widget build(BuildContext context) {
    final rede = this.rede;
    final contrato = contratoAtual;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        topInset + BrandTokens.spaceMd * fontScale,
        BrandTokens.spaceLg,
        BrandTokens.radiusFolha + BrandTokens.spaceMd,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Saudação + nome + sino de notificações.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
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
              const NotifBell(color: BrandTokens.capaInk),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          // Bloco de status completo: conexão + plano + (aparelhos +
          // atalho "Minha rede"), com degrade gracioso quando a rede
          // ainda não foi carregada (chip fica na linha principal).
          Container(
            padding: const EdgeInsets.all(16),
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
                    if (rede == null) ...[
                      const SizedBox(width: BrandTokens.spaceSm),
                      const _MinhaRedeChip(),
                    ],
                  ],
                ),
                if (rede != null)
                  Padding(
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
                        const SizedBox(width: BrandTokens.spaceSm),
                        const _MinhaRedeChip(),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          if (contrato != null && contrato.enderecoResumido.isNotEmpty) ...[
            const SizedBox(height: BrandTokens.spaceSm),
            _ContratoLinha(
              contrato: contrato,
              podeTrocar: podeTrocarContrato,
              onTrocar: onTrocar,
            ),
          ],
        ],
      ),
    );
  }
}

/// Layout natural do estado colapsado: faixa compacta de status (pill +
/// plano elidido + chip "Minha rede") e linha de contrato compacta,
/// centralizados verticalmente na banda útil acima do lábio da folha.
class _CollapsedLayout extends StatelessWidget {
  const _CollapsedLayout({
    required this.planoNome,
    required this.rede,
    required this.contratoAtual,
    required this.podeTrocarContrato,
    required this.onTrocar,
  });

  final String planoNome;
  final RedeAparelhosDto? rede;
  final ContratoResumoDto? contratoAtual;
  final bool podeTrocarContrato;
  final VoidCallback? onTrocar;

  @override
  Widget build(BuildContext context) {
    final contrato = contratoAtual;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: BrandTokens.spaceLg),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.max,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: BrandTokens.capaInk.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
            ),
            child: Row(
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
                const SizedBox(width: BrandTokens.spaceSm),
                const _MinhaRedeChip(),
              ],
            ),
          ),
          if (contrato != null && contrato.enderecoResumido.isNotEmpty) ...[
            const SizedBox(height: BrandTokens.spaceSm - 4),
            _ContratoLinha(
              contrato: contrato,
              podeTrocar: podeTrocarContrato,
              onTrocar: onTrocar,
              compact: true,
            ),
          ],
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
/// `compact` seleciona o tamanho reduzido usado no layout colapsado —
/// nenhuma posição/tamanho é interpolado, cada layout usa seus próprios
/// valores fixos.
class _ContratoLinha extends StatelessWidget {
  const _ContratoLinha({
    required this.contrato,
    required this.podeTrocar,
    required this.onTrocar,
    this.compact = false,
  });

  final ContratoResumoDto contrato;
  final bool podeTrocar;
  final VoidCallback? onTrocar;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final iconSize = compact ? 12.0 : 14.0;
    final fontSize = compact ? 11.0 : 12.0;
    final swapIconSize = compact ? 13.0 : 16.0;
    final linha = Row(
      children: [
        Icon(Icons.location_on_outlined,
            size: iconSize, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            contrato.enderecoResumido,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: BrandTokens.capaInk.withValues(alpha: 0.7),
              fontSize: fontSize,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (podeTrocar)
          Icon(Icons.swap_horiz_rounded,
              size: swapIconSize,
              color: BrandTokens.capaInk.withValues(alpha: 0.7)),
      ],
    );
    if (!podeTrocar || onTrocar == null) return linha;
    return GestureDetector(onTap: onTrocar, child: linha);
  }
}
