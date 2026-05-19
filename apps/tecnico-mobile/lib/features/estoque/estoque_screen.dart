import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'estoque_data.dart';

class EstoqueScreen extends ConsumerStatefulWidget {
  const EstoqueScreen({super.key});

  @override
  ConsumerState<EstoqueScreen> createState() => _EstoqueScreenState();
}

class _EstoqueScreenState extends ConsumerState<EstoqueScreen> {
  final _searchCtrl = TextEditingController();
  bool _soComSaldo = false;

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(estoqueSaldoProvider);
    final scheme = Theme.of(context).colorScheme;
    final query = _searchCtrl.text.trim().toLowerCase();

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Estoque'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(estoqueSaldoProvider),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _Erro(
          e: e,
          onRetry: () => ref.invalidate(estoqueSaldoProvider),
        ),
        data: (todas) {
          final filtradas = todas.where((l) {
            if (_soComSaldo && l.saldo <= 0) return false;
            if (query.isEmpty) return true;
            return l.nome.toLowerCase().contains(query) ||
                l.sku.toLowerCase().contains(query) ||
                l.categoria.toLowerCase().contains(query);
          }).toList();

          final totalItens = todas.fold<int>(
              0, (a, l) => a + (l.saldo > 0 ? l.saldo : 0));
          final categorias = <String>{for (final l in todas) l.categoria}.length;

          return Column(
            children: [
              // Header com resumo
              Container(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                color: scheme.surface,
                child: Row(
                  children: [
                    _Resumo(
                      label: 'Itens em estoque',
                      value: '$totalItens',
                      icon: Icons.inventory_2,
                      color: const Color(0xFF2563eb),
                    ),
                    const SizedBox(width: 12),
                    _Resumo(
                      label: 'Categorias',
                      value: '$categorias',
                      icon: Icons.category,
                      color: const Color(0xFF06b6d4),
                    ),
                  ],
                ),
              ),
              // Filtros
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
                child: Column(
                  children: [
                    TextField(
                      controller: _searchCtrl,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        prefixIcon: const Icon(Icons.search, size: 20),
                        hintText: 'Buscar por nome, SKU ou categoria',
                        isDense: true,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        suffixIcon: _searchCtrl.text.isNotEmpty
                            ? IconButton(
                                icon: const Icon(Icons.clear, size: 18),
                                onPressed: () {
                                  _searchCtrl.clear();
                                  setState(() {});
                                },
                              )
                            : null,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        FilterChip(
                          label: const Text('Apenas com saldo'),
                          selected: _soComSaldo,
                          onSelected: (v) => setState(() => _soComSaldo = v),
                        ),
                        const Spacer(),
                        Text(
                          '${filtradas.length} ${filtradas.length == 1 ? "item" : "itens"}',
                          style: TextStyle(
                            fontSize: 12,
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Expanded(
                child: filtradas.isEmpty
                    ? const _Vazio()
                    : RefreshIndicator(
                        onRefresh: () async =>
                            ref.invalidate(estoqueSaldoProvider),
                        child: ListView.builder(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.only(bottom: 16),
                          itemCount: filtradas.length,
                          itemBuilder: (_, i) =>
                              _ItemTile(linha: filtradas[i]),
                        ),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Resumo extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  const _Resumo({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.25)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 24, color: color),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: scheme.onSurface,
                    height: 1,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ItemTile extends StatelessWidget {
  final EstoqueLinha linha;
  const _ItemTile({required this.linha});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final temSaldo = linha.saldo > 0;
    final iconBg = _categoriaIconBg(linha.categoria);

    return Card(
      elevation: 0,
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: iconBg.bg.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: Icon(iconBg.icon, color: iconBg.bg, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    linha.nome,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Text(
                        linha.sku,
                        style: TextStyle(
                          fontSize: 11,
                          color: scheme.onSurfaceVariant,
                          fontFamily: 'monospace',
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '·',
                        style: TextStyle(color: scheme.onSurfaceVariant),
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          linha.categoria,
                          style: TextStyle(
                            fontSize: 11,
                            color: scheme.onSurfaceVariant,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  if (linha.serializado)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: const Color(0xFF8b5cf6)
                              .withValues(alpha: 0.13),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text(
                          'serializado',
                          style: TextStyle(
                            fontSize: 9.5,
                            color: Color(0xFF7c3aed),
                            fontWeight: FontWeight.w600,
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
                color: temSaldo
                    ? const Color(0xFF16a34a).withValues(alpha: 0.12)
                    : scheme.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${linha.saldo}',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: temSaldo
                      ? const Color(0xFF15803d)
                      : scheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  ({Color bg, IconData icon}) _categoriaIconBg(String cat) {
    final c = cat.toLowerCase();
    if (c.contains('cabo') || c.contains('drop')) {
      return (bg: const Color(0xFF2563eb), icon: Icons.cable);
    }
    if (c.contains('conector') || c.contains('emenda')) {
      return (bg: const Color(0xFF06b6d4), icon: Icons.electric_meter);
    }
    if (c.contains('roteador') || c.contains('ont') || c.contains('onu')) {
      return (bg: const Color(0xFF7c3aed), icon: Icons.router);
    }
    if (c.contains('switch') || c.contains('rack')) {
      return (bg: const Color(0xFF16a34a), icon: Icons.hub);
    }
    if (c.contains('ferr') || c.contains('alicate')) {
      return (bg: const Color(0xFFd97706), icon: Icons.build);
    }
    return (bg: const Color(0xFF64748b), icon: Icons.inventory_2);
  }
}

class _Vazio extends StatelessWidget {
  const _Vazio();
  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 80),
        Icon(
          Icons.inventory_2_outlined,
          size: 56,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(height: 12),
        Text(
          'Nenhum item encontrado.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _Erro extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _Erro({required this.e, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.error_outline, size: 56),
        const SizedBox(height: 12),
        Text(e.toString(), textAlign: TextAlign.center),
        const SizedBox(height: 12),
        FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
      ]),
    );
  }
}
