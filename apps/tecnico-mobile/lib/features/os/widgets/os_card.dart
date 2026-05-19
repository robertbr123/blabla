import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Card rico de OS — usado na lista. Mostra:
/// - faixa lateral colorida por status (visual rápido)
/// - código + status badge
/// - nome do cliente (destaque)
/// - endereço com ícone
/// - problema (truncado em 2 linhas)
/// - agendamento (relativo: "hoje 14:30", "amanhã", "atrasada 2d")
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
    final c = _StatusStyle.of(status);
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Card(
      elevation: 0,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: scheme.outlineVariant.withValues(alpha: 0.5),
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Faixa lateral colorida (4dp).
              Container(width: 4, color: c.color),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Linha 1: codigo + status badge
                      Row(
                        children: [
                          Text(
                            codigo,
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.2,
                            ),
                          ),
                          const Spacer(),
                          _StatusPill(style: c),
                        ],
                      ),
                      const SizedBox(height: 6),
                      // Cliente
                      Text(
                        nomeCliente ?? 'Cliente —',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          height: 1.2,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      // Endereço
                      Row(
                        children: [
                          Icon(
                            Icons.place_outlined,
                            size: 14,
                            color: scheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              endereco,
                              style: TextStyle(
                                fontSize: 12.5,
                                color: scheme.onSurfaceVariant,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      // Problema
                      Text(
                        problema,
                        style: TextStyle(
                          fontSize: 13,
                          color: scheme.onSurface.withValues(alpha: 0.85),
                          height: 1.35,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (agendamentoAt != null) ...[
                        const SizedBox(height: 8),
                        _Agendamento(
                          at: agendamentoAt!,
                          dark: isDark,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: Icon(
                  Icons.chevron_right,
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusStyle {
  final String label;
  final Color color;
  final IconData icon;
  const _StatusStyle(this.label, this.color, this.icon);

  static _StatusStyle of(String status) {
    switch (status) {
      case 'pendente':
        return const _StatusStyle('Pendente', Color(0xFFf59e0b), Icons.hourglass_top);
      case 'em_andamento':
        return const _StatusStyle('Em andamento', Color(0xFF2563eb), Icons.directions_run);
      case 'concluida':
        return const _StatusStyle('Concluída', Color(0xFF16a34a), Icons.check_circle);
      case 'cancelada':
        return const _StatusStyle('Cancelada', Color(0xFF6b7280), Icons.cancel);
      default:
        return _StatusStyle(status, const Color(0xFF6b7280), Icons.help_outline);
    }
  }
}

class _StatusPill extends StatelessWidget {
  final _StatusStyle style;
  const _StatusPill({required this.style});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: style.color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: style.color.withValues(alpha: 0.30)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(style.icon, size: 12, color: style.color),
          const SizedBox(width: 4),
          Text(
            style.label,
            style: TextStyle(
              color: style.color,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _Agendamento extends StatelessWidget {
  final DateTime at;
  final bool dark;
  const _Agendamento({required this.at, required this.dark});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final local = at.toLocal();
    final diff = local.difference(now);
    final scheme = Theme.of(context).colorScheme;

    String label;
    Color color;
    IconData icon;

    if (diff.isNegative && (-diff).inHours > 24) {
      final dias = (-diff).inDays;
      label = 'Atrasada $dias ${dias == 1 ? "dia" : "dias"}';
      color = const Color(0xFFdc2626);
      icon = Icons.warning_amber;
    } else if (diff.isNegative) {
      label = 'Atrasada ${(-diff).inHours}h';
      color = const Color(0xFFdc2626);
      icon = Icons.warning_amber;
    } else if (_isSameDay(local, now)) {
      label = 'Hoje ${DateFormat('HH:mm').format(local)}';
      color = const Color(0xFFd97706);
      icon = Icons.today;
    } else if (_isSameDay(local, now.add(const Duration(days: 1)))) {
      label = 'Amanhã ${DateFormat('HH:mm').format(local)}';
      color = const Color(0xFF2563eb);
      icon = Icons.event;
    } else {
      label = DateFormat("dd/MM 'às' HH:mm").format(local);
      color = scheme.onSurfaceVariant;
      icon = Icons.event;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: dark ? 0.18 : 0.10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}
