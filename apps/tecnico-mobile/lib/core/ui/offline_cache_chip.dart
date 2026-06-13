import 'package:flutter/material.dart';

/// Pílula discreta exibida quando offline, com a idade do cache servido.
class OfflineCacheChip extends StatelessWidget {
  const OfflineCacheChip({super.key, this.syncedAt});

  final DateTime? syncedAt;

  static const _amber = Color(0xFFB45309);
  static const _amberBase = Color(0xFFF59E0B);

  @override
  Widget build(BuildContext context) {
    final label = syncedAt == null
        ? 'Offline'
        : 'Offline · dados de ${_idade(syncedAt!)}';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: _amberBase.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _amberBase.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_rounded, size: 16, color: _amber),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: _amber,
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _idade(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 1) return 'agora';
    if (d.inMinutes < 60) return 'há ${d.inMinutes} min';
    if (d.inHours < 24) return 'há ${d.inHours} h';
    return 'há ${d.inDays} ${d.inDays == 1 ? 'dia' : 'dias'}';
  }
}
