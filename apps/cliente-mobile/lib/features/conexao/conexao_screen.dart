import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/conexao_repository.dart';
import '../../core/api/dto.dart';
import '../../core/branding/brand_tokens.dart';

class ConexaoScreen extends ConsumerWidget {
  const ConexaoScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(conexaoProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Status da conexão'),
        elevation: 0,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(conexaoProvider);
          await ref.read(conexaoProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _Error(
            onRetry: () => ref.invalidate(conexaoProvider),
          ),
          data: (c) => ListView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            children: [
              _StatusHero(conexao: c),
              const SizedBox(height: BrandTokens.spaceLg),
              _InfoCards(conexao: c),
              const SizedBox(height: BrandTokens.spaceLg),
              if (c.status != 'ativo')
                _CtaSuporte(status: c.status)
              else ...[
                const _GerenciarRedeButton(),
                const SizedBox(height: BrandTokens.spaceLg),
                const _DicaPanel(),
              ],
              if (!c.temTelemetriaReal) ...[
                const SizedBox(height: BrandTokens.spaceLg),
                const _TelemetriaInfo(),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusHero extends StatefulWidget {
  const _StatusHero({required this.conexao});
  final ConexaoDto conexao;

  @override
  State<_StatusHero> createState() => _StatusHeroState();
}

class _StatusHeroState extends State<_StatusHero>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  ({LinearGradient grad, String titulo, String sub, IconData icon}) _ui() {
    switch (widget.conexao.status) {
      case 'ativo':
        return (
          grad: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF14B8B0), Color(0xFF22E0A1)],
          ),
          titulo: 'Serviço ativo',
          sub: 'Seu contrato esta vigente.',
          icon: Icons.check_circle_rounded,
        );
      case 'suspenso':
        return (
          grad: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFE8A33D), Color(0xFFF59E0B)],
          ),
          titulo: 'Serviço suspenso',
          sub: widget.conexao.motivo.isNotEmpty
              ? widget.conexao.motivo
              : 'Serviço temporariamente pausado.',
          icon: Icons.pause_circle_filled_rounded,
        );
      case 'cancelado':
        return (
          grad: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [BrandTokens.danger, Color(0xFFB12B40)],
          ),
          titulo: 'Contrato cancelado',
          sub: widget.conexao.motivo.isNotEmpty
              ? widget.conexao.motivo
              : 'Contrato encerrado.',
          icon: Icons.block_rounded,
        );
      default:
        return (
          grad: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF6B7280), Color(0xFF374151)],
          ),
          titulo: 'Status indisponivel',
          sub: 'Não conseguimos identificar seu contrato no momento.',
          icon: Icons.help_outline_rounded,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ui = _ui();
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: ui.grad,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.elevation2,
      ),
      child: Row(
        children: [
          AnimatedBuilder(
            animation: _ctrl,
            builder: (_, __) {
              final scale = 1.0 + (_ctrl.value * 0.06);
              return Transform.scale(
                scale: scale,
                child: Container(
                  width: 76,
                  height: 76,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.18),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withOpacity(0.30),
                      width: 2,
                    ),
                  ),
                  child: Icon(ui.icon, color: Colors.white, size: 38),
                ),
              );
            },
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  ui.titulo,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  ui.sub,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    height: 1.3,
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

class _InfoCards extends StatelessWidget {
  const _InfoCards({required this.conexao});
  final ConexaoDto conexao;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(
          color: isDark ? Colors.white12 : BrandTokens.divider,
        ),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        children: [
          _InfoRow(
            icon: Icons.wifi_rounded,
            label: 'Plano',
            value: conexao.plano ?? '—',
            color: BrandTokens.primary,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
            ),
            child: Divider(
              height: 1,
              color: isDark ? Colors.white10 : BrandTokens.divider,
            ),
          ),
          _InfoRow(
            icon: Icons.location_on_outlined,
            label: 'Cidade',
            value: conexao.cidade ?? '—',
            color: BrandTokens.info,
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withOpacity(0.14),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: BrandTokens.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  value,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CtaSuporte extends StatelessWidget {
  const _CtaSuporte({required this.status});
  final String status;

  String _texto() {
    if (status == 'suspenso') {
      return 'Serviço suspenso? Vamos resolver — abra um chamado pra normalizar seu acesso.';
    }
    if (status == 'cancelado') {
      return 'Quer voltar a ser cliente Ondeline? Fale com a gente.';
    }
    return 'Algo não parece certo. Fale com o suporte.';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.warning.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.warning.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(
                Icons.support_agent_rounded,
                color: BrandTokens.warning,
              ),
              const SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  _texto(),
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          FilledButton.icon(
            icon: const Icon(Icons.message_outlined, size: 18),
            label: const Text('Falar com suporte'),
            onPressed: () => context.push('/suporte/novo'),
          ),
        ],
      ),
    );
  }
}

class _DicaPanel extends StatelessWidget {
  const _DicaPanel();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.success.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.success.withOpacity(0.25)),
      ),
      child: const Row(
        children: [
          Icon(Icons.lightbulb_outline, color: BrandTokens.success),
          SizedBox(width: BrandTokens.spaceSm),
          Expanded(
            child: Text(
              'Tudo certo com seu contrato. Sem internet em casa? '
              'Confira a FAQ pra dicas rapidas antes de abrir um chamado.',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

class _TelemetriaInfo extends StatelessWidget {
  const _TelemetriaInfo();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: BrandTokens.spaceSm),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            size: 14,
            color: BrandTokens.textSecondary,
          ),
          SizedBox(width: 6),
          Expanded(
            child: Text(
              'Status mostrado vem do seu contrato. Telemetria em tempo real (sinal óptico, queda recente) chega em breve.',
              style: TextStyle(
                fontSize: 11,
                color: BrandTokens.textSecondary,
                fontWeight: FontWeight.w500,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GerenciarRedeButton extends StatelessWidget {
  const _GerenciarRedeButton();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: BrandTokens.primary.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.wifi_rounded, color: BrandTokens.primary),
              SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  'Quer trocar a senha do seu WiFi? Faça por aqui, na hora.',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
              ),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          FilledButton.icon(
            icon: const Icon(Icons.settings_rounded, size: 18),
            label: const Text('Gerenciar rede WiFi'),
            onPressed: () => context.push('/rede'),
          ),
        ],
      ),
    );
  }
}

class _Error extends StatelessWidget {
  const _Error({required this.onRetry});
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline,
              color: BrandTokens.danger,
              size: 40,
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Não conseguimos carregar o status agora.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
          ],
        ),
      ),
    );
  }
}
