import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/conexao_repository.dart';
import '../../../core/branding/brand_tokens.dart';

/// Pill no hero da home com status real do contrato (B1).
/// - `ativo` (verde): contrato vigente.
/// - `suspenso` (amarelo): pendencia, contrato pausado.
/// - `cancelado` (vermelho): contrato encerrado.
/// - `desconhecido` (cinza): sem dado.
///
/// Tap abre a tela /conexao com detalhe.
class ConnectionStatusPill extends ConsumerWidget {
  const ConnectionStatusPill({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(conexaoProvider);
    return async.when(
      data: (c) => _Pill(
        status: c.status,
        onTap: () => context.push('/conexao'),
      ),
      loading: () => const _Pill(status: 'loading'),
      error: (_, __) => const _Pill(status: 'desconhecido'),
    );
  }
}

class _Pill extends StatefulWidget {
  const _Pill({required this.status, this.onTap});
  final String status;
  final VoidCallback? onTap;

  @override
  State<_Pill> createState() => _PillState();
}

class _PillState extends State<_Pill>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  ({Color color, String label, IconData? icon}) _info() {
    switch (widget.status) {
      case 'ativo':
        return (
          color: const Color(0xFF22E0A1),
          label: 'Servico ativo',
          icon: null,
        );
      case 'suspenso':
        return (
          color: BrandTokens.warning,
          label: 'Suspenso',
          icon: Icons.warning_amber_rounded,
        );
      case 'cancelado':
        return (
          color: BrandTokens.danger,
          label: 'Cancelado',
          icon: Icons.block_rounded,
        );
      case 'loading':
        return (
          color: Colors.white54,
          label: 'Verificando...',
          icon: null,
        );
      default:
        return (
          color: Colors.white54,
          label: 'Sem dado',
          icon: null,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final info = _info();
    final child = Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.14),
        borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
        border: Border.all(color: Colors.white.withOpacity(0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedBuilder(
            animation: _ctrl,
            builder: (_, __) {
              final t = _ctrl.value;
              return Stack(
                alignment: Alignment.center,
                children: [
                  Container(
                    width: 8 + t * 6,
                    height: 8 + t * 6,
                    decoration: BoxDecoration(
                      color: info.color.withOpacity(0.25 * (1 - t)),
                      shape: BoxShape.circle,
                    ),
                  ),
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: info.color,
                      shape: BoxShape.circle,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(width: 8),
          if (info.icon != null) ...[
            Icon(info.icon, color: Colors.white, size: 14),
            const SizedBox(width: 4),
          ],
          Text(
            info.label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
    if (widget.onTap == null) return child;
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
        child: child,
      ),
    );
  }
}
