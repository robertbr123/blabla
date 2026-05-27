import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../cliente_data.dart';

/// Lista os materiais que o tecnico baixou do estoque pra essa instalacao.
class ClienteMateriaisSection extends ConsumerWidget {
  final String clienteId;
  const ClienteMateriaisSection({super.key, required this.clienteId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(clienteMateriaisProvider(clienteId));
    final scheme = Theme.of(context).colorScheme;

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: async.when(
          loading: () => const SizedBox(
            height: 40,
            child: Center(
              child: SizedBox(
                height: 18,
                width: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
          error: (_, __) => Text(
            'Não consegui carregar materiais.',
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          data: (items) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.inventory_2_outlined,
                      size: 16, color: scheme.onSurfaceVariant),
                  const SizedBox(width: 6),
                  Text(
                    'MATERIAIS USADOS · ${items.length}',
                    style: TextStyle(
                      fontSize: 11,
                      letterSpacing: 0.5,
                      fontWeight: FontWeight.w700,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  if (items.isNotEmpty) ...[
                    const Spacer(),
                    Text(
                      '${_totalUnidades(items)} unidade(s)',
                      style: TextStyle(
                        fontSize: 11,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 8),
              if (items.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Text(
                    'Nenhum material consumido nessa instalação.',
                    style: TextStyle(
                      fontSize: 13,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                )
              else
                Column(
                  children: items
                      .map((m) => _MaterialLinha(material: m))
                      .toList(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  int _totalUnidades(List<MaterialUsado> items) =>
      items.fold(0, (a, m) => a + m.quantidade);
}

class _MaterialLinha extends StatelessWidget {
  final MaterialUsado material;
  const _MaterialLinha({required this.material});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final cat = _categoria(material.categoria);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: cat.color.withValues(alpha: 0.13),
              borderRadius: BorderRadius.circular(8),
            ),
            alignment: Alignment.center,
            child: Icon(cat.icon, size: 18, color: cat.color),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  material.nome,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  material.sku,
                  style: TextStyle(
                    fontSize: 11,
                    color: scheme.onSurfaceVariant,
                    fontFamily: 'monospace',
                  ),
                ),
                if (material.serial != null && material.serial!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: GestureDetector(
                      onTap: () {
                        Clipboard.setData(
                          ClipboardData(text: material.serial!),
                        );
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('serial copiado'),
                            duration: Duration(milliseconds: 800),
                          ),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color:
                              const Color(0xFF8b5cf6).withValues(alpha: 0.13),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.qr_code_2,
                                size: 10, color: Color(0xFF7c3aed)),
                            const SizedBox(width: 3),
                            Text(
                              material.serial!,
                              style: const TextStyle(
                                fontSize: 10.5,
                                fontFamily: 'monospace',
                                color: Color(0xFF7c3aed),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 3),
                            const Icon(Icons.copy,
                                size: 9, color: Color(0xFF7c3aed)),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF16a34a).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${material.quantidade} ${material.unidadeLabel}',
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: Color(0xFF15803d),
              ),
            ),
          ),
        ],
      ),
    );
  }

  ({IconData icon, Color color}) _categoria(String cat) {
    final c = cat.toLowerCase();
    if (c.contains('cabo') || c.contains('drop')) {
      return (icon: Icons.cable, color: const Color(0xFF2563eb));
    }
    if (c.contains('conector') || c.contains('emenda')) {
      return (icon: Icons.electric_meter, color: const Color(0xFF06b6d4));
    }
    if (c.contains('onu') || c.contains('roteador')) {
      return (icon: Icons.router, color: const Color(0xFF7c3aed));
    }
    if (c.contains('switch') || c.contains('rack')) {
      return (icon: Icons.hub, color: const Color(0xFF16a34a));
    }
    return (icon: Icons.inventory_2, color: const Color(0xFF64748b));
  }
}
