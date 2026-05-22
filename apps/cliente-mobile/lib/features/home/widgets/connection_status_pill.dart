import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

enum ConnectionStatus { online, instavel, offline, unknown }

/// Pill com bolinha pulsante mostrando status do link.
/// Por enquanto recebe status mock — bloco B1 vai plugar API real.
class ConnectionStatusPill extends StatefulWidget {
  const ConnectionStatusPill({super.key, this.status = ConnectionStatus.online});
  final ConnectionStatus status;

  @override
  State<ConnectionStatusPill> createState() => _ConnectionStatusPillState();
}

class _ConnectionStatusPillState extends State<ConnectionStatusPill>
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
      case ConnectionStatus.online:
        return (
          color: const Color(0xFF22E0A1),
          label: 'Conexao estavel',
          icon: null,
        );
      case ConnectionStatus.instavel:
        return (
          color: BrandTokens.warning,
          label: 'Conexao instavel',
          icon: Icons.warning_amber_rounded,
        );
      case ConnectionStatus.offline:
        return (
          color: BrandTokens.danger,
          label: 'Sem conexao',
          icon: Icons.wifi_off_rounded,
        );
      case ConnectionStatus.unknown:
        return (
          color: Colors.white54,
          label: 'Verificando...',
          icon: null,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final info = _info();
    return Container(
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
  }
}
