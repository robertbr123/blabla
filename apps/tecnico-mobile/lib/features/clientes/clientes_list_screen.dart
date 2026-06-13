import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/branding/brand_kpi_card.dart';
import '../../core/ui/ios_glass_header.dart';
import '../../core/branding/brand_status_pill.dart' show BrandTone;
import '../../core/ui/app_state_panel.dart';
import 'cliente_data.dart';
import 'widgets/cliente_card.dart';

class ClientesListScreen extends ConsumerStatefulWidget {
  const ClientesListScreen({super.key});

  @override
  ConsumerState<ClientesListScreen> createState() => _ClientesListScreenState();
}

class _ClientesListScreenState extends ConsumerState<ClientesListScreen> {
  final _busca = TextEditingController();
  final _buscaFocus = FocusNode();
  Timer? _debounce;
  String? _sgpFilter; // null = todos, 'synced' | 'pending'

  @override
  void dispose() {
    _buscaFocus.dispose();
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
      backgroundColor: scheme.surface,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(clientesListProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            IosGlassHeader(
              title: 'Clientes',
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Atualizar',
                  onPressed: () => ref.invalidate(clientesListProvider),
                ),
              ],
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Builder(builder: (_) {
                  final visiveis = async.maybeWhen(
                      data: (page) => page.items.length, orElse: () => 0);
                  final pendentes = async.maybeWhen(
                      data: (page) =>
                          page.items.where((c) => c.sgpSyncedAt == null).length,
                      orElse: () => 0);
                  return BrandKpiCard(
                    label: 'Pendentes de sincronização',
                    value: '$pendentes',
                    icon: Icons.cloud_off_outlined,
                    tone: pendentes > 0 ? BrandTone.warning : BrandTone.success,
                    onTap: visiveis > 0
                        ? () {
                            _toggleSgp(
                                _sgpFilter == 'pending' ? null : 'pending');
                          }
                        : null,
                  );
                }),
              ),
            ),
            SliverPersistentHeader(
              pinned: true,
              delegate: _ClientesSearchHeader(
                controller: _busca,
                focusNode: _buscaFocus,
                currentText: _busca.text,
                sgpFilter: _sgpFilter,
                background: scheme.surface,
                onSearchChanged: _onBuscaChanged,
                onClearSearch: () {
                  _busca.clear();
                  _onBuscaChanged('');
                },
                onToggleSgp: _toggleSgp,
              ),
            ),
            ...async.when<List<Widget>>(
              loading: () => const [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _StateBody(
                    child: AppStatePanel.loading(
                      title: 'Carregando clientes',
                      message:
                          'Atualizando a base do dia para você buscar cidade, serial e status SGP sem ruído.',
                    ),
                  ),
                ),
              ],
              error: (e, _) => [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _ErroView(
                    e: e,
                    onRetry: () => ref.invalidate(clientesListProvider),
                  ),
                ),
              ],
              data: (page) {
                if (page.items.isEmpty) {
                  return [
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: _VazioView(
                        hasSearch: _busca.text.isNotEmpty || _sgpFilter != null,
                      ),
                    ),
                  ];
                }
                return [
                  SliverPadding(
                    padding: const EdgeInsets.only(top: 2, bottom: 88),
                    sliver: SliverList.builder(
                      itemCount: page.items.length,
                      itemBuilder: (_, i) {
                        final c = page.items[i];
                        return ClienteCard(
                          item: c,
                          onTap: () => context.push('/clientes/${c.id}'),
                        );
                      },
                    ),
                  ),
                ];
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Header pinned com a busca + filtros SGP (fica fixo sob o IosGlassHeader).
class _ClientesSearchHeader extends SliverPersistentHeaderDelegate {
  _ClientesSearchHeader({
    required this.controller,
    required this.focusNode,
    required this.currentText,
    required this.sgpFilter,
    required this.background,
    required this.onSearchChanged,
    required this.onClearSearch,
    required this.onToggleSgp,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final String currentText;
  final String? sgpFilter;
  final Color background;
  final ValueChanged<String> onSearchChanged;
  final VoidCallback onClearSearch;
  final ValueChanged<String?> onToggleSgp;

  static const _height = 116.0;

  @override
  double get minExtent => _height;

  @override
  double get maxExtent => _height;

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      color: background,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 8),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextField(
            controller: controller,
            focusNode: focusNode,
            onChanged: onSearchChanged,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search, size: 20),
              hintText: 'Buscar por nome, CPF, cidade, serial…',
              isDense: true,
              suffixIcon: controller.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      onPressed: onClearSearch,
                    )
                  : null,
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _FilterChip(
                  label: 'Todos',
                  selected: sgpFilter == null,
                  onTap: () => onToggleSgp(null),
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'Sincronizado',
                  icon: Icons.cloud_done,
                  color: scheme.primary,
                  selected: sgpFilter == 'synced',
                  onTap: () => onToggleSgp('synced'),
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'Pendente SGP',
                  icon: Icons.cloud_off,
                  color: const Color(0xFFF59E0B),
                  selected: sgpFilter == 'pending',
                  onTap: () => onToggleSgp('pending'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _ClientesSearchHeader oldDelegate) {
    return currentText != oldDelegate.currentText ||
        sgpFilter != oldDelegate.sgpFilter ||
        background != oldDelegate.background ||
        controller != oldDelegate.controller ||
        focusNode != oldDelegate.focusNode;
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
