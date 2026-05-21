import 'package:flutter/material.dart';

import '../../../core/branding/brand_status_pill.dart';
import '../../../core/ui/app_surfaces.dart';
import '../../os/widgets/cliente_avatar.dart';
import '../cliente_data.dart';

class ClienteCard extends StatelessWidget {
  final ClienteListItem item;
  final VoidCallback onTap;
  final bool destaqueInstaladoPorMim;

  const ClienteCard({
    super.key,
    required this.item,
    required this.onTap,
    this.destaqueInstaladoPorMim = false,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final synced = item.sgpSyncedAt != null;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: AppSurfaceCard(
        padding: EdgeInsets.zero,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClienteAvatar(nome: item.nome, size: 52),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.nome,
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
                                const SizedBox(height: 5),
                                Text(
                                  _maskCpf(item.cpf),
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: scheme.onSurfaceVariant,
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          BrandStatusPill(
                            label: synced ? 'SGP OK' : 'Pendente',
                            icon: synced
                                ? Icons.cloud_done_outlined
                                : Icons.cloud_off_outlined,
                            tone: synced ? BrandTone.success : BrandTone.warning,
                            size: BrandPillSize.sm,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _MetaRow(
                        icon: Icons.place_outlined,
                        child: Text(
                          _enderecoCurto(item),
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
                        child: Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _Pill(
                              icon: Icons.wifi,
                              label: item.planNome.length > 30
                                  ? '${item.planNome.substring(0, 30)}…'
                                  : item.planNome,
                              color: const Color(0xFF2563eb),
                            ),
                            _Pill(
                              icon: Icons.engineering_outlined,
                              label: item.installerNome,
                              color: scheme.primary,
                            ),
                            if (destaqueInstaladoPorMim)
                              const _Pill(
                                icon: Icons.verified_user_outlined,
                                label: 'instalei eu',
                                color: Color(0xFF16a34a),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Icon(
                    Icons.chevron_right_rounded,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _maskCpf(String cpf) {
    final d = cpf.replaceAll(RegExp(r'\D'), '');
    if (d.length == 11) {
      return '${d.substring(0, 3)}.${d.substring(3, 6)}.${d.substring(6, 9)}-${d.substring(9)}';
    }
    if (d.length == 14) {
      return '${d.substring(0, 2)}.${d.substring(2, 5)}.${d.substring(5, 8)}/${d.substring(8, 12)}-${d.substring(12)}';
    }
    return cpf;
  }

  String _enderecoCurto(ClienteListItem item) {
    final partes = <String>[
      item.address,
      item.number,
      if (item.neighborhood != null && item.neighborhood!.isNotEmpty)
        item.neighborhood!,
      item.city,
    ];
    return partes.join(', ');
  }
}

class _MetaRow extends StatelessWidget {
  final IconData icon;
  final Widget child;

  const _MetaRow({
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 14,
          color: scheme.onSurfaceVariant,
        ),
        const SizedBox(width: 6),
        Expanded(child: child),
      ],
    );
  }
}

class _Pill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _Pill({required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
