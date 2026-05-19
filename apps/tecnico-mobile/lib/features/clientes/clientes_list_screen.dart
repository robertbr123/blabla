import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'cliente_data.dart';
import 'widgets/cliente_card.dart';

class ClientesListScreen extends ConsumerStatefulWidget {
  const ClientesListScreen({super.key});

  @override
  ConsumerState<ClientesListScreen> createState() =>
      _ClientesListScreenState();
}

class _ClientesListScreenState extends ConsumerState<ClientesListScreen> {
  final _busca = TextEditingController();
  Timer? _debounce;
  String? _sgpFilter; // null = todos, 'synced' | 'pending'

  @override
  void dispose() {
    _busca.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onBuscaChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      ref.read(clienteListFilterProvider.notifier).state =
          ClienteListFilter(q: v, sgpStatus: _sgpFilter);
    });
  }

  void _toggleSgp(String? value) {
    setState(() => _sgpFilter = value);
    ref.read(clienteListFilterProvider.notifier).state =
        ClienteListFilter(q: _busca.text, sgpStatus: value);
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(clientesListProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Clientes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(clientesListProvider),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/clientes/novo'),
        icon: const Icon(Icons.person_add),
        label: const Text('Novo'),
      ),
      body: Column(
        children: [
          // Barra de busca
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
            child: TextField(
              controller: _busca,
              onChanged: _onBuscaChanged,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search, size: 20),
                hintText: 'Buscar por cidade, bairro, serial…',
                isDense: true,
                suffixIcon: _busca.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _busca.clear();
                          _onBuscaChanged('');
                        },
                      )
                    : null,
              ),
            ),
          ),
          // Chips de filtro SGP
          SizedBox(
            height: 44,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _FilterChip(
                  label: 'Todos',
                  selected: _sgpFilter == null,
                  onTap: () => _toggleSgp(null),
                ),
                const SizedBox(width: 6),
                _FilterChip(
                  label: 'Sincronizado',
                  icon: Icons.cloud_done,
                  color: const Color(0xFF16a34a),
                  selected: _sgpFilter == 'synced',
                  onTap: () => _toggleSgp('synced'),
                ),
                const SizedBox(width: 6),
                _FilterChip(
                  label: 'Pendente SGP',
                  icon: Icons.cloud_off,
                  color: const Color(0xFFf59e0b),
                  selected: _sgpFilter == 'pending',
                  onTap: () => _toggleSgp('pending'),
                ),
              ],
            ),
          ),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => _ErroView(
                e: e,
                onRetry: () => ref.invalidate(clientesListProvider),
              ),
              data: (page) {
                if (page.items.isEmpty) {
                  return _VazioView(
                    hasSearch: _busca.text.isNotEmpty || _sgpFilter != null,
                  );
                }
                return RefreshIndicator(
                  onRefresh: () async => ref.invalidate(clientesListProvider),
                  child: ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.only(top: 4, bottom: 88),
                    itemCount: page.items.length,
                    itemBuilder: (_, i) {
                      final c = page.items[i];
                      return ClienteCard(
                        item: c,
                        onTap: () => context.push('/clientes/${c.id}'),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final IconData? icon;
  final Color? color;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    this.icon,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final activeColor = color ?? scheme.primary;
    return Center(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: selected
                ? activeColor.withValues(alpha: 0.13)
                : scheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selected ? activeColor : scheme.outlineVariant,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 14, color: selected ? activeColor : scheme.onSurfaceVariant),
                const SizedBox(width: 5),
              ],
              Text(
                label,
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  color: selected ? activeColor : scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VazioView extends StatelessWidget {
  final bool hasSearch;
  const _VazioView({required this.hasSearch});
  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 80),
        Icon(
          hasSearch ? Icons.search_off : Icons.person_off,
          size: 56,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(height: 12),
        Text(
          hasSearch
              ? 'Nenhum cliente encontrado com esses filtros.'
              : 'Nenhum cliente cadastrado ainda.\nToque em "Novo" pra começar.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _ErroView extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _ErroView({required this.e, required this.onRetry});
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
