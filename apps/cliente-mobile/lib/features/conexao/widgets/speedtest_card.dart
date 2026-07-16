import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';
import '../speedtest_service.dart';

enum _Fase { idle, ping, download, upload, concluido, erro }

/// Card de speedtest in-app (topo da folha da tela Conexão).
///
/// Estados: inicial (botão), rodando (velocímetro semicircular ao vivo),
/// resultado (3 métricas) e erro (mensagem + retry).
class SpeedtestCard extends StatefulWidget {
  const SpeedtestCard({super.key});

  @override
  State<SpeedtestCard> createState() => _SpeedtestCardState();
}

class _SpeedtestCardState extends State<SpeedtestCard> {
  final _service = SpeedtestService();

  _Fase _fase = _Fase.idle;
  double _liveMbps = 0;
  double? _pingMs;
  double? _downloadMbps;
  double? _uploadMbps;
  String? _erroMsg;

  @override
  void dispose() {
    _service.cancel();
    super.dispose();
  }

  Future<void> _iniciar() async {
    setState(() {
      _fase = _Fase.ping;
      _liveMbps = 0;
      _pingMs = null;
      _downloadMbps = null;
      _uploadMbps = null;
      _erroMsg = null;
    });
    try {
      final ping = await _service.ping();
      if (!mounted) return;
      setState(() {
        _pingMs = ping;
        _fase = _Fase.download;
        _liveMbps = 0;
      });

      final download = await _service.download((mbps) {
        if (!mounted) return;
        setState(() => _liveMbps = mbps);
      });
      if (!mounted) return;
      setState(() {
        _downloadMbps = download;
        _fase = _Fase.upload;
        _liveMbps = 0;
      });

      final upload = await _service.upload((mbps) {
        if (!mounted) return;
        setState(() => _liveMbps = mbps);
      });
      if (!mounted) return;
      setState(() {
        _uploadMbps = upload;
        _fase = _Fase.concluido;
      });
    } on SpeedtestFalhou catch (e) {
      if (!mounted) return;
      setState(() {
        _fase = _Fase.erro;
        _erroMsg = e.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _fase = _Fase.erro;
        _erroMsg = 'Algo deu errado ao medir sua velocidade.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: isDark ? Colors.white12 : BrandTokens.divider,
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: switch (_fase) {
        _Fase.idle => _EstadoInicial(onTestar: _iniciar),
        _Fase.ping ||
        _Fase.download ||
        _Fase.upload =>
          _EstadoRodando(fase: _fase, liveMbps: _liveMbps),
        _Fase.concluido => _EstadoResultado(
            downloadMbps: _downloadMbps ?? 0,
            uploadMbps: _uploadMbps ?? 0,
            pingMs: _pingMs ?? 0,
            onTestarDeNovo: _iniciar,
          ),
        _Fase.erro => _EstadoErro(
            mensagem: _erroMsg ?? 'Não foi possível medir sua velocidade.',
            onRetry: _iniciar,
          ),
      },
    );
  }
}

class _EstadoInicial extends StatelessWidget {
  const _EstadoInicial({required this.onTestar});
  final VoidCallback onTestar;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: BrandTokens.primary.withValues(alpha: 0.12),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.speed_rounded,
            color: BrandTokens.primary,
            size: 30,
          ),
        ),
        const SizedBox(height: BrandTokens.spaceMd),
        const Text(
          'Teste a velocidade da sua conexão',
          textAlign: TextAlign.center,
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
        ),
        const SizedBox(height: 4),
        const Text(
          'Medimos ping, download e upload até a Cloudflare.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: BrandTokens.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: BrandTokens.spaceMd),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            icon: const Icon(Icons.speed_rounded, size: 18),
            label: const Text('Testar velocidade'),
            onPressed: onTestar,
          ),
        ),
      ],
    );
  }
}

class _EstadoRodando extends StatelessWidget {
  const _EstadoRodando({required this.fase, required this.liveMbps});
  final _Fase fase;
  final double liveMbps;

  String get _label => switch (fase) {
        _Fase.ping => 'Medindo ping…',
        _Fase.download => 'Medindo download…',
        _Fase.upload => 'Medindo upload…',
        _ => '',
      };

  IconData get _icon => switch (fase) {
        _Fase.ping => Icons.network_ping_rounded,
        _Fase.download => Icons.arrow_downward_rounded,
        _Fase.upload => Icons.arrow_upward_rounded,
        _ => Icons.speed_rounded,
      };

  /// Progresso "aproximado" do arco: como não há um alvo fixo de Mbps,
  /// usamos a fase corrente pra dar sensação de avanço (1/3, 2/3, cheio),
  /// mais uma pequena animação do ponteiro em cima do valor ao vivo.
  double get _progresso => switch (fase) {
        _Fase.ping => 0.15,
        _Fase.download => 0.55,
        _Fase.upload => 0.9,
        _ => 0,
      };

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          height: 130,
          width: 220,
          child: CustomPaint(
            painter: _GaugePainter(progresso: _progresso),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.only(top: 28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      fase == _Fase.ping
                          ? '…'
                          : liveMbps.toStringAsFixed(0),
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        color: BrandTokens.primary,
                        letterSpacing: -0.5,
                      ),
                    ),
                    if (fase != _Fase.ping)
                      const Text(
                        'Mbps',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: BrandTokens.textSecondary,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(_icon, size: 16, color: BrandTokens.primary),
            const SizedBox(width: 6),
            Text(
              _label,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: BrandTokens.primary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Velocímetro semicircular: arco de fundo + arco de progresso com
/// gradiente da marca (BrandTokens.gradientPrimary).
class _GaugePainter extends CustomPainter {
  _GaugePainter({required this.progresso});
  final double progresso;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height - 10);
    final radius = math.min(size.width / 2, size.height) - 12;
    const startAngle = math.pi; // 180°
    const sweepTotal = math.pi; // semicírculo

    final bgPaint = Paint()
      ..color = BrandTokens.divider
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepTotal,
      false,
      bgPaint,
    );

    final progressPaint = Paint()
      ..shader = BrandTokens.gradientPrimary.createShader(
        Rect.fromCircle(center: center, radius: radius),
      )
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepTotal * progresso.clamp(0, 1),
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) =>
      oldDelegate.progresso != progresso;
}

class _EstadoResultado extends StatelessWidget {
  const _EstadoResultado({
    required this.downloadMbps,
    required this.uploadMbps,
    required this.pingMs,
    required this.onTestarDeNovo,
  });

  final double downloadMbps;
  final double uploadMbps;
  final double pingMs;
  final VoidCallback onTestarDeNovo;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _Metrica(
                icon: Icons.arrow_downward_rounded,
                label: 'Download',
                valor: downloadMbps.toStringAsFixed(1),
                unidade: 'Mbps',
                destaque: true,
              ),
            ),
            Expanded(
              child: _Metrica(
                icon: Icons.arrow_upward_rounded,
                label: 'Upload',
                valor: uploadMbps.toStringAsFixed(1),
                unidade: 'Mbps',
              ),
            ),
            Expanded(
              child: _Metrica(
                icon: Icons.network_ping_rounded,
                label: 'Ping',
                valor: pingMs.toStringAsFixed(0),
                unidade: 'ms',
              ),
            ),
          ],
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        TextButton.icon(
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: const Text('Testar de novo'),
          onPressed: onTestarDeNovo,
        ),
        const Text(
          'Medido até a Cloudflare — resultado aproximado.',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 11,
            color: BrandTokens.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _Metrica extends StatelessWidget {
  const _Metrica({
    required this.icon,
    required this.label,
    required this.valor,
    required this.unidade,
    this.destaque = false,
  });

  final IconData icon;
  final String label;
  final String valor;
  final String unidade;
  final bool destaque;

  @override
  Widget build(BuildContext context) {
    final cor = destaque ? BrandTokens.primary : BrandTokens.textSecondary;
    return Column(
      children: [
        Icon(icon, size: 16, color: cor),
        const SizedBox(height: 4),
        Text(
          valor,
          style: TextStyle(
            fontSize: destaque ? 24 : 18,
            fontWeight: FontWeight.w900,
            color: destaque ? BrandTokens.primary : null,
            letterSpacing: -0.5,
          ),
        ),
        Text(
          '$label ($unidade)',
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 11,
            color: BrandTokens.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _EstadoErro extends StatelessWidget {
  const _EstadoErro({required this.mensagem, required this.onRetry});
  final String mensagem;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const Icon(
          Icons.wifi_off_rounded,
          color: BrandTokens.danger,
          size: 32,
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        Text(
          mensagem,
          textAlign: TextAlign.center,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: BrandTokens.spaceMd),
        TextButton.icon(
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: const Text('Tentar de novo'),
          onPressed: onRetry,
        ),
      ],
    );
  }
}
