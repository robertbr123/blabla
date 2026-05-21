import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_state_panel.dart';
import '../../core/ui/app_status_chip.dart';
import '../../core/ui/app_surfaces.dart';
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
        loading: () => const _StateBody(
          child: AppStatePanel.loading(
            title: 'Carregando estoque',
            message: 'Conferindo saldo e categorias para sua próxima visita.',
          ),
        ),
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

          final totalItens =
              todas.fold<int>(0, (a, l) => a + (l.saldo > 0 ? l.saldo : 0));
          final categorias =
              <String>{for (final l in todas) l.categoria}.length;
          final hasActiveRefinement = query.isNotEmpty || _soComSaldo;

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
                child: AppSurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const AppSectionHeader(
                        title: 'Visão do estoque',
                        subtitle:
                            'Consulte saldo, categorias e filtros rápidos antes de sair para a próxima visita.',
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          AppStatusChip(
                            label: '$totalItens itens disponíveis',
                            tone: AppStatusTone.info,
                          ),
                          AppStatusChip(
                            label: '$categorias categorias ativas',
                            tone: AppStatusTone.warning,
                          ),
                          AppStatusChip(
                            label: _soComSaldo
                                ? 'Somente com saldo'
                                : 'Todos os materiais',
                            tone: _soComSaldo
                                ? AppStatusTone.success
                                : AppStatusTone.neutral,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          _Resumo(
                            label: 'Itens em estoque',
                            value: '$totalItens',
                            icon: Icons.inventory_2_outlined,
                            color: scheme.primary,
                          ),
                          const SizedBox(width: 12),
                          _Resumo(
                            label: 'Categorias',
                            value: '$categorias',
                            icon: Icons.category_outlined,
                            color: scheme.secondary,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _searchCtrl,
                        onChanged: (_) => setState(() {}),
                        decoration: InputDecoration(
                          prefixIcon: const Icon(Icons.search, size: 20),
                          hintText: 'Buscar por nome, SKU ou categoria',
                          isDense: true,
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
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          FilterChip(
                            label: const Text('Apenas com saldo'),
                            selected: _soComSaldo,
                            onSelected: (v) => setState(() => _soComSaldo = v),
                          ),
                          const Spacer(),
                          Text(
                            '${filtradas.length} ${filtradas.length == 1 ? "item visível" : "itens visíveis"}',
                            style: TextStyle(
                              fontSize: 12,
                              color: scheme.onSurfaceVariant,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async => ref.invalidate(estoqueSaldoProvider),
                  child: filtradas.isEmpty
                      ? _Vazio(hasActiveRefinement: hasActiveRefinement)
                      : ListView.builder(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.only(bottom: 24),
                          itemCount: filtradas.length,
                          itemBuilder: (_, i) => Padding(
                            padding: EdgeInsets.fromLTRB(
                              16,
                              i == 0 ? 2 : 0,
                              16,
                              12,
                            ),
                            child: _ItemTile(linha: filtradas[i]),
                          ),
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
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              alignment: Alignment.center,
              child: Icon(icon, size: 20, color: color),
            ),
            const SizedBox(height: 14),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: scheme.onSurface,
                height: 1,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 11.5,
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
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

    return AppSurfaceCard(
      padding: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: iconBg.bg.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(14),
              ),
              alignment: Alignment.center,
              child: Icon(iconBg.icon, color: iconBg.bg, size: 21),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          linha.nome,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: scheme.onSurface,
                            height: 1.2,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      AppStatusChip(
                        label: temSaldo ? '${linha.saldo} un.' : 'Sem saldo',
                        tone: temSaldo
                            ? AppStatusTone.success
                            : AppStatusTone.warning,
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    linha.sku,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: scheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                      fontFamily: 'monospace',
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      AppStatusChip(
                        label: linha.categoria,
                        tone: AppStatusTone.neutral,
                      ),
                      if (linha.serializado)
                        const AppStatusChip(
                          label: 'Serializado',
                          tone: AppStatusTone.info,
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
  const _Vazio({required this.hasActiveRefinement});

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 2, 16, 24),
      children: [
        AppStatePanel.empty(
          title: 'Nenhum item encontrado.',
          message: hasActiveRefinement
              ? 'Ajuste a busca ou desative o filtro para revisar todo o material disponível.'
              : 'Nenhum item de estoque foi disponibilizado para este técnico até o momento.',
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
