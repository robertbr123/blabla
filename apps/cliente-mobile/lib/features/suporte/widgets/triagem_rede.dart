import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';

/// Varredura diagnóstica antes do chamado "Sem internet": consulta status
/// (ONU online) + aparelhos (total + selo de saúde) via GenieACS e mostra
/// pro cliente com orientação por cenário. Nunca bloqueia: erro/timeout/
/// sem ONU → onConcluir(null) (segue pro formulário sem diagnóstico).
class TriagemRede extends ConsumerStatefulWidget {
  const TriagemRede({
    super.key,
    required this.onConcluir,
    required this.onResolveu,
  });

  /// Cliente quer seguir com o chamado. diagnostico == null → varredura
  /// não rolou (bypass).
  final ValueChanged<Map<String, dynamic>?> onConcluir;

  /// Cliente desistiu do chamado ("Resolveu, valeu!").
  final VoidCallback onResolveu;

  @override
  ConsumerState<TriagemRede> createState() => _TriagemRedeState();
}

enum _Fase { escaneando, resultado }

class _TriagemRedeState extends ConsumerState<TriagemRede>
    with SingleTickerProviderStateMixin {
  _Fase _fase = _Fase.escaneando;
  bool? _online;
  int? _totalAparelhos;
  List<String> _nomesAparelhos = const [];
  String _saude = 'indisponivel';
  Map<String, dynamic>? _diagnostico;

  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();

  @override
  void initState() {
    super.initState();
    _varrer();
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _varrer() async {
    try {
      final repo = ref.read(redeRepositoryProvider);
      final results = await Future.wait([
        repo.status(),
        repo.aparelhos(),
      ]).timeout(const Duration(seconds: 12));

      final statusDto = results[0] as RedeStatusDto;
      final aparelhosDto = results[1] as RedeAparelhosDto;

      // Qualquer encontrada == false → bypass
      if (!statusDto.encontrada || !aparelhosDto.encontrada) {
        if (!mounted) return;
        widget.onConcluir(null);
        return;
      }

      final diag = <String, dynamic>{
        'online': statusDto.online,
        'total_aparelhos': aparelhosDto.total,
        'saude': aparelhosDto.saude,
        'timestamp': DateTime.now().toUtc().toIso8601String(),
      };

      if (!mounted) return;
      setState(() {
        _online = statusDto.online;
        _totalAparelhos = aparelhosDto.total;
        _nomesAparelhos = aparelhosDto.aparelhos.map((a) => a.nomeExibicao).toList();
        _saude = aparelhosDto.saude;
        _diagnostico = diag;
        _fase = _Fase.resultado;
      });
    } on Object {
      // Timeout/erro/sem ONU → segue pro formulário sem bloquear.
      if (!mounted) return;
      widget.onConcluir(null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return switch (_fase) {
      _Fase.escaneando => _buildEscaneando(context),
      _Fase.resultado => _buildResultado(context),
    };
  }

  Widget _buildEscaneando(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _RadarPulsante(controller: _pulse),
            const SizedBox(height: BrandTokens.spaceLg),
            Text(
              'Verificando sua conexão…',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            Text(
              'Estamos olhando sua rede antes do chamado.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultado(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: BrandTokens.spaceSm),
      children: [
        Text(
          'Diagnóstico da sua rede',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        _CardOnu(online: _online ?? false),
        const SizedBox(height: BrandTokens.spaceMd),
        _CardAparelhos(
          total: _totalAparelhos ?? 0,
          nomes: _nomesAparelhos,
        ),
        const SizedBox(height: BrandTokens.spaceMd),
        _CardSinal(saude: _saude),
        const SizedBox(height: BrandTokens.spaceLg),
        _Orientacao(
          saude: _saude,
          online: _online ?? false,
          totalAparelhos: _totalAparelhos,
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: widget.onResolveu,
                child: const Text('Resolveu, valeu!'),
              ),
            ),
            const SizedBox(width: BrandTokens.spaceMd),
            Expanded(
              child: FilledButton(
                onPressed: () => widget.onConcluir(_diagnostico),
                child: const Text('Ainda preciso de ajuda'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ────────────────────────── Radar pulsante ──────────────────────────

class _RadarPulsante extends StatelessWidget {
  const _RadarPulsante({required this.controller});
  final AnimationController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (_, __) {
        final t = controller.value; // 0.0 → 1.0
        return SizedBox(
          width: 120,
          height: 120,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Círculo externo (alpha mais baixo, expande mais)
              _PulseCircle(
                scale: 0.6 + t * 0.4,
                alpha: (0.25 * (1 - t)).clamp(0.0, 1.0),
                size: 120,
              ),
              // Círculo médio
              _PulseCircle(
                scale: 0.55 + t * 0.3,
                alpha: (0.40 * (1 - t)).clamp(0.0, 1.0),
                size: 90,
              ),
              // Círculo interno (mais opaco, menor)
              _PulseCircle(
                scale: 0.5 + t * 0.2,
                alpha: (0.55 * (1 - t)).clamp(0.0, 1.0),
                size: 64,
              ),
              // Ícone central
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: BrandTokens.primary,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.wifi_rounded, color: Colors.white, size: 24),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _PulseCircle extends StatelessWidget {
  const _PulseCircle({
    required this.scale,
    required this.alpha,
    required this.size,
  });
  final double scale;
  final double alpha;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Transform.scale(
      scale: scale,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: BrandTokens.primary.withValues(alpha: alpha),
        ),
      ),
    );
  }
}

// ────────────────────────── Cards de resultado ──────────────────────────

class _CardOnu extends StatelessWidget {
  const _CardOnu({required this.online});
  final bool online;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cor = online ? BrandTokens.success : BrandTokens.danger;
    final icon = online ? Icons.router_rounded : Icons.signal_wifi_off_rounded;
    final label = online ? 'ONU online' : 'ONU offline';
    final sub = online
        ? 'Seu equipamento está se comunicando.'
        : 'Seu equipamento não está respondendo.';

    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: cor.withValues(alpha: 0.30)),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: cor.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Icon(icon, color: cor, size: 22),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 15, color: cor)),
                Text(sub,
                    style: const TextStyle(
                        color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CardAparelhos extends StatefulWidget {
  const _CardAparelhos({required this.total, required this.nomes});
  final int total;
  final List<String> nomes;

  @override
  State<_CardAparelhos> createState() => _CardAparelhosState();
}

class _CardAparelhosState extends State<_CardAparelhos> {
  bool _expandido = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
            color: isDark ? Colors.white12 : BrandTokens.divider),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: widget.nomes.isEmpty
                ? null
                : () => setState(() => _expandido = !_expandido),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            child: Padding(
              padding: const EdgeInsets.all(BrandTokens.spaceMd),
              child: Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: BrandTokens.primary.withValues(alpha: 0.12),
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusSm),
                    ),
                    child: const Icon(Icons.devices_rounded,
                        color: BrandTokens.primary, size: 22),
                  ),
                  const SizedBox(width: BrandTokens.spaceMd),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Dispositivos conectados (${widget.total})',
                          style: const TextStyle(
                              fontWeight: FontWeight.w800, fontSize: 15),
                        ),
                        Text(
                          widget.nomes.isEmpty
                              ? 'Nenhum aparelho conectado agora.'
                              : 'Toque para ver a lista',
                          style: const TextStyle(
                              color: BrandTokens.textSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  if (widget.nomes.isNotEmpty)
                    Icon(
                      _expandido
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      color: BrandTokens.textSecondary,
                    ),
                ],
              ),
            ),
          ),
          if (_expandido && widget.nomes.isNotEmpty) ...[
            const Divider(height: 1),
            ...widget.nomes.map(
              (nome) => Padding(
                padding: const EdgeInsets.symmetric(
                    horizontal: BrandTokens.spaceMd,
                    vertical: BrandTokens.spaceSm),
                child: Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color:
                            BrandTokens.primary.withValues(alpha: 0.10),
                        borderRadius:
                            BorderRadius.circular(BrandTokens.radiusSm),
                      ),
                      child: const Icon(Icons.devices_other_rounded,
                          color: BrandTokens.primary, size: 16),
                    ),
                    const SizedBox(width: BrandTokens.spaceMd),
                    Expanded(
                      child: Text(
                        nome,
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 13),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
          ],
        ],
      ),
    );
  }
}

class _CardSinal extends StatelessWidget {
  const _CardSinal({required this.saude});
  final String saude;

  ({Color cor, IconData icon, String label, String sub}) _ui() {
    switch (saude) {
      case 'excelente':
        return (
          cor: BrandTokens.success,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal excelente',
          sub: 'Sua fibra está com sinal ótimo.',
        );
      case 'boa':
        return (
          cor: BrandTokens.primary,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal bom',
          sub: 'Sua conexão está saudável.',
        );
      case 'fraca':
        return (
          cor: BrandTokens.warning,
          icon: Icons.signal_cellular_alt_2_bar_rounded,
          label: 'Sinal fraco',
          sub: 'Pode valer a pena falar com o suporte.',
        );
      default:
        return (
          cor: BrandTokens.info,
          icon: Icons.wifi_tethering_rounded,
          label: 'Conexão ativa',
          sub: 'Sua rede está no ar.',
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final ui = _ui();
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : ui.cor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: ui.cor.withValues(alpha: 0.30)),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: ui.cor.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Icon(ui.icon, color: ui.cor, size: 22),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(ui.label,
                    style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                        color: ui.cor)),
                Text(ui.sub,
                    style: const TextStyle(
                        color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ────────────────────────── Orientação por cenário ──────────────────────────

class _Orientacao extends StatelessWidget {
  const _Orientacao({
    required this.saude,
    required this.online,
    required this.totalAparelhos,
  });
  final String saude;
  final bool online;
  final int? totalAparelhos;

  @override
  Widget build(BuildContext context) {
    final IconData icon;
    final Color cor;
    final String titulo;
    final String texto;

    if (saude == 'fraca' || !online) {
      icon = Icons.warning_amber_rounded;
      cor = BrandTokens.warning;
      titulo = 'Encontramos um problema do nosso lado';
      texto = 'O sinal da tua fibra está fraco — isso explica a lentidão. '
          'Abre o chamado que a gente resolve.';
    } else if (totalAparelhos != null && totalAparelhos! >= 10) {
      icon = Icons.people_alt_rounded;
      cor = BrandTokens.info;
      titulo = 'Tem bastante gente na rede';
      texto = 'São $totalAparelhos aparelhos conectados — em horário de pico '
          'isso pesa. Desconectar alguns pode resolver.';
    } else {
      icon = Icons.check_circle_outline_rounded;
      cor = BrandTokens.success;
      titulo = 'Tua conexão parece saudável';
      texto = 'Sinal ótimo e ONU online. Reiniciar o roteador '
          '(tira da tomada 10s) resolve a maioria dos casos.';
    }

    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: cor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: cor.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: cor, size: 24),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  titulo,
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: cor,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  texto,
                  style: const TextStyle(
                    color: BrandTokens.textPrimary,
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
