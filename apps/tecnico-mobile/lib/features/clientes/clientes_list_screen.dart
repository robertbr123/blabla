import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_state_panel.dart';
import '../../core/ui/app_status_chip.dart';
import '../../core/ui/app_surfaces.dart';
import 'cliente_data.dart';
import 'widgets/cliente_card.dart';

class ClientesListScreen extends ConsumerStatefulWidget {
  const ClientesListScreen({super.key});

  @override
  ConsumerState<ClientesListScreen> createState() => _ClientesListScreenState();
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
    setState(() {});
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
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
            child: AppSurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AppSectionHeader(
                    title: 'Base de clientes',
                    subtitle:
                        'Busque por cidade, bairro ou serial e acompanhe o status SGP sem sair da fila.',
                  ),
                  const SizedBox(height: 16),
                  TextField(
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
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      AppStatusChip(
                        label: _sgpFilter == 'synced'
                            ? 'Somente sincronizados'
                            : _sgpFilter == 'pending'
                                ? 'Somente pendentes SGP'
                                : 'Todos os clientes',
                        tone: _sgpFilter == 'pending'
                            ? AppStatusTone.warning
                            : _sgpFilter == 'synced'
                                ? AppStatusTone.success
                                : AppStatusTone.info,
                      ),
                      _SummaryPill(
                        icon: Icons.people_alt_outlined,
                        label:
                            '${async.maybeWhen(data: (page) => page.items.length, orElse: () => 0)} visíveis',
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    height: 44,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        _FilterChip(
                          label: 'Todos',
                          selected: _sgpFilter == null,
                          onTap: () => _toggleSgp(null),
                        ),
                        const SizedBox(width: 8),
                        _FilterChip(
                          label: 'Sincronizado',
                          icon: Icons.cloud_done,
                          color: const Color(0xFF16a34a),
                          selected: _sgpFilter == 'synced',
                          onTap: () => _toggleSgp('synced'),
                        ),
                        const SizedBox(width: 8),
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
                ],
              ),
            ),
          ),
          Expanded(
            child: async.when(
              loading: () => const _StateBody(
                child: AppStatePanel.loading(
                  title: 'Carregando clientes',
                  message:
                      'Atualizando a base do dia para você buscar cidade, serial e status SGP sem ruído.',
                ),
              ),
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
                    padding: const EdgeInsets.only(top: 2, bottom: 88),
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

class _SummaryPill extends StatelessWidget {
  final IconData icon;
  final String label;

  const _SummaryPill({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: scheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: scheme.onSurfaceVariant,
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
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
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
                Icon(
                  icon,
                  size: 14,
                  color: selected ? activeColor : scheme.onSurfaceVariant,
                ),
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
      padding: const EdgeInsets.fromLTRB(16, 32, 16, 24),
      children: [
        AppStatePanel.empty(
          title:
              hasSearch ? 'Nenhum cliente encontrado' : 'Base vazia por aqui',
          message: hasSearch
              ? 'Ajuste a busca ou os filtros SGP para ampliar a lista visível.'
              : 'Nenhum cliente foi sincronizado ainda. Toque em "Novo" para começar um cadastro em campo.',
          icon: hasSearch ? Icons.search_off_rounded : Icons.person_off_rounded,
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
    final panel = isOfflineException(e)
        ? AppStatePanel.offline(
            title: 'Sem conexão para atualizar clientes',
            message:
                'Sem rede e sem cache disponível para essa lista. Tente novamente quando o sinal voltar.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          )
        : AppStatePanel.error(
            title: 'Não foi possível carregar clientes',
            message:
                'A lista não respondeu como esperado. Atualize novamente para retomar a busca do dia.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          );

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 32, 16, 24),
      children: [panel],
    );
  }
}

class _StateBody extends StatelessWidget {
  final Widget child;
  const _StateBody({required this.child});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: child,
        ),
      ),
    );
  }
}
