import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/branding/brand_kpi_card.dart';
import '../../core/branding/brand_status_pill.dart' show BrandTone;
import '../../core/ui/app_state_panel.dart';
import '../../core/ui/app_surfaces.dart';
import '../../core/ui/ios_glass_header.dart';
import 'estoque_data.dart';

class EstoqueScreen extends ConsumerStatefulWidget {
  const EstoqueScreen({super.key});

  @override
  ConsumerState<EstoqueScreen> createState() => _EstoqueScreenState();
}

class _EstoqueScreenState extends ConsumerState<EstoqueScreen> {
  final _searchCtrl = TextEditingController();
  // FocusNode estável: a busca vive num SliverPersistentHeader pinned que
  // rebuilda no setState do debounce; o node próprio mantém o teclado aberto.
  final _searchFocus = FocusNode();
  // Por padrão esconde itens zerados — técnico só vê o que realmente tem.
  bool _mostrarZerados = false;
  Timer? _searchDebounce;

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchFocus.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  /// Debounce do filtro: o texto digitado aparece na hora (controller), mas o
  /// recálculo da lista só dispara 250ms após parar de digitar.
  void _onSearchChanged() {
    _searchDebounce?.cancel();
    _searchDebounce =
        Timer(const Duration(milliseconds: 250), () {
      if (mounted) setState(() {});
    });
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(estoqueSaldoProvider);
    final scheme = Theme.of(context).colorScheme;
    final query = _searchCtrl.text.trim().toLowerCase();

    return Scaffold(
      backgroundColor: scheme.surface,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(estoqueSaldoProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            IosGlassHeader(
              title: 'Estoque',
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Atualizar',
                  onPressed: () => ref.invalidate(estoqueSaldoProvider),
                ),
              ],
            ),
            ...async.when<List<Widget>>(
              loading: () => const [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _StateBody(
                    child: AppStatePanel.loading(
                      title: 'Carregando estoque',
                      message:
                          'Conferindo saldo e categorias para sua próxima visita.',
                    ),
                  ),
                ),
              ],
              error: (e, _) => [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _Erro(
                    e: e,
                    onRetry: () => ref.invalidate(estoqueSaldoProvider),
                  ),
                ),
              ],
              data: (todas) {
                final filtradas = todas.where((l) {
                  if (!_mostrarZerados && l.saldo <= 0) return false;
                  if (query.isEmpty) return true;
                  return l.nome.toLowerCase().contains(query) ||
                      l.sku.toLowerCase().contains(query) ||
                      l.categoria.toLowerCase().contains(query);
                }).toList();

                final totalItens = todas.fold<int>(
                    0, (a, l) => a + (l.saldo > 0 ? l.saldo : 0));
                final categorias =
                    <String>{for (final l in todas) l.categoria}.length;
                final hasZerosOcultos =
                    !_mostrarZerados && todas.any((l) => l.saldo <= 0);
                final hasActiveRefinement = query.isNotEmpty || _mostrarZerados;

                return [
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Itens',
                              value: '$totalItens',
                              icon: Icons.inventory_2_outlined,
                              tone: BrandTone.info,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Categorias',
                              value: '$categorias',
                              icon: Icons.category_outlined,
                              tone: BrandTone.warning,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: BrandKpiCard(
                              label: 'Visíveis',
                              value: '${filtradas.length}',
                              icon: Icons.visibility_outlined,
                              tone: BrandTone.success,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  SliverPersistentHeader(
                    pinned: true,
                    delegate: _SearchHeaderDelegate(
                      controller: _searchCtrl,
                      focusNode: _searchFocus,
                      currentText: _searchCtrl.text,
                      mostrarZerados: _mostrarZerados,
                      hasActiveRefinement: hasActiveRefinement,
                      background: scheme.surface,
                      onSearchChanged: _onSearchChanged,
                      onClearSearch: () {
                        _searchCtrl.clear();
                        setState(() {});
                      },
                      onToggleZerados: (v) =>
                          setState(() => _mostrarZerados = v),
                      onClearAll: () {
                        _searchCtrl.clear();
                        setState(() => _mostrarZerados = false);
                      },
                    ),
                  ),
                  if (filtradas.isEmpty)
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: _Vazio(
                        hasActiveRefinement: hasActiveRefinement,
                        hasZerosOcultos: hasZerosOcultos,
                      ),
                    )
                  else
                    SliverList.builder(
                      itemCount: filtradas.length,
                      itemBuilder: (_, i) => Padding(
                        padding:
                            EdgeInsets.fromLTRB(16, i == 0 ? 2 : 0, 16, 12),
                        child: _ItemTile(linha: filtradas[i]),
                      ),
                    ),
                  const SliverToBoxAdapter(child: SizedBox(height: 24)),
                ];
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Header pinned com a busca + filtro do estoque (fica fixo sob o IosGlassHeader).
class _SearchHeaderDelegate extends SliverPersistentHeaderDelegate {
  _SearchHeaderDelegate({
    required this.controller,
    required this.focusNode,
    required this.currentText,
    required this.mostrarZerados,
    required this.hasActiveRefinement,
    required this.background,
    required this.onSearchChanged,
    required this.onClearSearch,
    required this.onToggleZerados,
    required this.onClearAll,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final String currentText;
  final bool mostrarZerados;
  final bool hasActiveRefinement;
  final Color background;
  final VoidCallback onSearchChanged;
  final VoidCallback onClearSearch;
  final ValueChanged<bool> onToggleZerados;
  final VoidCallback onClearAll;

  static const _height = 112.0;

  @override
  double get minExtent => _height;

  @override
  double get maxExtent => _height;

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: background,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 8),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextField(
            controller: controller,
            focusNode: focusNode,
            onChanged: (_) => onSearchChanged(),
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search, size: 20),
              hintText: 'Buscar por nome, SKU ou categoria',
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
          Row(
            children: [
              FilterChip(
                label: const Text('Mostrar zerados'),
                selected: mostrarZerados,
                onSelected: onToggleZerados,
                visualDensity: VisualDensity.compact,
              ),
              const Spacer(),
              if (hasActiveRefinement)
                TextButton.icon(
                  onPressed: onClearAll,
                  icon: const Icon(Icons.clear_all, size: 16),
                  label: const Text('Limpar'),
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _SearchHeaderDelegate oldDelegate) {
    return mostrarZerados != oldDelegate.mostrarZerados ||
        hasActiveRefinement != oldDelegate.hasActiveRefinement ||
        background != oldDelegate.background ||
        currentText != oldDelegate.currentText ||
        controller != oldDelegate.controller;
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

    return AppSurfaceCard(
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: iconBg.bg.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              alignment: Alignment.center,
              child: Icon(iconBg.icon, color: iconBg.bg, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Text(
                          linha.nome,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: scheme.onSurface,
                            height: 1.1,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 9,
                          vertical: 5,
                        ),
                        decoration: BoxDecoration(
                          color: (temSaldo
                                  ? const Color(0xFF16a34a)
                                  : scheme.error)
                              .withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          temSaldo ? '${linha.saldo} un.' : '0 un.',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: temSaldo
                                ? const Color(0xFF166534)
                                : scheme.error,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          linha.sku,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11.5,
                            color: scheme.onSurfaceVariant,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'monospace',
                            letterSpacing: 0.2,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          linha.categoria,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11.5,
                            color: scheme.onSurfaceVariant,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      if (linha.serializado)
                        Padding(
                          padding: const EdgeInsets.only(left: 8),
                          child: Text(
                            'Serializado',
                            style: TextStyle(
                              fontSize: 10.5,
                              color: scheme.primary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
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
  final bool hasActiveRefinement;
  final bool hasZerosOcultos;
  const _Vazio({
    required this.hasActiveRefinement,
    required this.hasZerosOcultos,
  });

  @override
  Widget build(BuildContext context) {
    final String message;
    if (hasActiveRefinement) {
      message =
          'Ajuste a busca ou ative "Mostrar zerados" para ver todo o material.';
    } else if (hasZerosOcultos) {
      message =
          'Você está sem saldo nos itens disponíveis. Ative "Mostrar zerados" para ver o catálogo completo.';
    } else {
      message =
          'Nenhum item de estoque foi disponibilizado para este técnico até o momento.';
    }
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 2, 16, 24),
      children: [
        AppStatePanel.empty(
          title: 'Nenhum item encontrado.',
          message: message,
          icon: Icons.inventory_2_outlined,
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
    final panel = isOfflineException(e)
        ? AppStatePanel.offline(
            title: 'Sem conexão para atualizar estoque',
            message:
                'Sem rede e sem snapshot local disponível para este saldo. Tente novamente quando o sinal voltar.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          )
        : AppStatePanel.error(
            title: 'Não foi possível carregar o estoque',
            message:
                'O saldo não respondeu como esperado. Atualize novamente para revisar seus materiais.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          );

    return _StateBody(child: panel);
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
