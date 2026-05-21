import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/branding/brand_status_pill.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/app_surfaces.dart';
import 'cliente_avatar.dart';

class OsCard extends StatelessWidget {
  final String id;
  final String codigo;
  final String status;
  final String problema;
  final String endereco;
  final String? nomeCliente;
  final DateTime? agendamentoAt;
  final VoidCallback onTap;

  const OsCard({
    super.key,
    required this.id,
    required this.codigo,
    required this.status,
    required this.problema,
    required this.endereco,
    required this.nomeCliente,
    required this.agendamentoAt,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final statusStyle = _StatusStyle.of(status);
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: AppSurfaceCard(
        padding: EdgeInsets.zero,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClienteAvatar(nome: nomeCliente, size: 48),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            nomeCliente ?? 'Cliente —',
                            style: TextStyle(
                              color: scheme.onSurface,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              height: 1.15,
                              letterSpacing: -0.2,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            codigo,
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: scheme.onSurfaceVariant,
                              letterSpacing: 0.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    BrandStatusPill(
                      label: statusStyle.label,
                      icon: statusStyle.icon,
                      tone: statusStyle.tone,
                      size: BrandPillSize.sm,
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _MetaRow(
                  icon: Icons.place_outlined,
                  child: Text(
                    endereco,
                    style: TextStyle(
                      fontSize: 13,
                      color: scheme.onSurfaceVariant,
                      height: 1.35,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerLow,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: _MetaRow(
                    icon: Icons.bolt_rounded,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    child: Text(
                      problema,
                      style: TextStyle(
                        fontSize: 13.5,
                        color: scheme.onSurface.withValues(alpha: 0.88),
                        height: 1.4,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: agendamentoAt != null
                          ? _Agendamento(at: agendamentoAt!)
                          : const _HintPill(
                              icon: Icons.info_outline_rounded,
                              label: 'Sem agendamento informado',
                            ),
                    ),
                    const SizedBox(width: 12),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: scheme.onSurfaceVariant,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusStyle {
  final String label;
  final IconData icon;
  final BrandTone tone;

  const _StatusStyle(this.label, this.icon, this.tone);

  static _StatusStyle of(String status) {
    switch (status) {
      case 'pendente':
        return const _StatusStyle(
          'Pendente',
          Icons.hourglass_top_outlined,
          BrandTone.info,
        );
      case 'em_andamento':
        return const _StatusStyle(
          'Em andamento',
          Icons.play_circle_outline,
          BrandTone.warning,
        );
      case 'concluida':
        return const _StatusStyle(
          'Concluída',
          Icons.check_circle_outline,
          BrandTone.success,
        );
      case 'cancelada':
        return const _StatusStyle(
          'Cancelada',
          Icons.cancel_outlined,
          BrandTone.danger,
        );
      default:
        return _StatusStyle(
          status,
          Icons.help_outline,
          BrandTone.neutral,
        );
    }
  }
}

class _MetaRow extends StatelessWidget {
  final IconData icon;
  final Widget child;
  final CrossAxisAlignment crossAxisAlignment;

  const _MetaRow({
    required this.icon,
    required this.child,
    this.crossAxisAlignment = CrossAxisAlignment.center,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Row(
      crossAxisAlignment: crossAxisAlignment,
      children: [
        Icon(icon, size: 16, color: scheme.onSurfaceVariant),
        const SizedBox(width: 8),
        Expanded(child: child),
      ],
    );
  }
}

class _Agendamento extends StatelessWidget {
  final DateTime at;

  const _Agendamento({required this.at});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final local = at.toLocal();
    final diff = local.difference(now);
    final brand = context.brand;
    final scheme = Theme.of(context).colorScheme;

    String label;
    Color color;
    IconData icon;

    if (diff.isNegative && (-diff).inHours > 24) {
      final dias = (-diff).inDays;
      label = 'Atrasada $dias ${dias == 1 ? "dia" : "dias"}';
      color = brand.danger;
      icon = Icons.warning_amber_rounded;
    } else if (diff.isNegative) {
      label = 'Atrasada ${(-diff).inHours}h';
      color = brand.danger;
      icon = Icons.warning_amber_rounded;
    } else if (_sameDay(local, now)) {
      label = 'Hoje ${DateFormat('HH:mm').format(local)}';
      color = brand.warning;
      icon = Icons.today_rounded;
    } else if (_sameDay(local, now.add(const Duration(days: 1)))) {
      label = 'Amanhã ${DateFormat('HH:mm').format(local)}';
      color = brand.info;
      icon = Icons.event_rounded;
    } else {
      label = DateFormat("dd/MM 'às' HH:mm").format(local);
      color = scheme.onSurfaceVariant;
      icon = Icons.event_rounded;
    }

    return _HintPill(icon: icon, label: label, color: color);
  }

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

class _HintPill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;

  const _HintPill({
    required this.icon,
    required this.label,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final resolvedColor = color ?? scheme.onSurfaceVariant;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: resolvedColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: resolvedColor),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label,
              style: TextStyle(
                color: resolvedColor,
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
