import 'package:flutter/material.dart';

enum OsHomeFilter { todas, pendente, andamento, concluida, cancelada }

extension OsHomeFilterX on OsHomeFilter {
  String get label {
    switch (this) {
      case OsHomeFilter.todas:
        return 'Todas';
      case OsHomeFilter.pendente:
        return 'Pendentes';
      case OsHomeFilter.andamento:
        return 'Em andamento';
      case OsHomeFilter.concluida:
        return 'Concluídas';
      case OsHomeFilter.cancelada:
        return 'Canceladas';
    }
  }

  String get listTitle {
    switch (this) {
      case OsHomeFilter.todas:
        return 'Lista de OS';
      case OsHomeFilter.pendente:
        return 'Pendentes';
      case OsHomeFilter.andamento:
        return 'Em andamento';
      case OsHomeFilter.concluida:
        return 'Concluídas';
      case OsHomeFilter.cancelada:
        return 'Canceladas';
    }
  }

  String listSubtitle(int count) {
    switch (this) {
      case OsHomeFilter.todas:
        return '$count ordens em foco no seu dia.';
      case OsHomeFilter.pendente:
        return '$count ordens aguardando a primeira ação.';
      case OsHomeFilter.andamento:
        return '$count visitas em execução agora.';
      case OsHomeFilter.concluida:
        return '$count ordens já encerradas.';
      case OsHomeFilter.cancelada:
        return '$count ordens que exigem replanejamento.';
    }
  }

  bool matches(String status) {
    switch (this) {
      case OsHomeFilter.todas:
        return true;
      case OsHomeFilter.pendente:
        return status == 'pendente';
      case OsHomeFilter.andamento:
        return status == 'em_andamento';
      case OsHomeFilter.concluida:
        return status == 'concluida';
      case OsHomeFilter.cancelada:
        return status == 'cancelada';
    }
  }
}

class HomeFilterStrip extends StatelessWidget {
  const HomeFilterStrip({
    super.key,
    required this.filters,
    required this.selected,
    required this.onSelected,
  });

  final List<OsHomeFilter> filters;
  final OsHomeFilter selected;
  final ValueChanged<OsHomeFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return SizedBox(
      height: 42,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemBuilder: (context, index) {
          final filter = filters[index];
          final isSelected = filter == selected;
          return Semantics(
            key: ValueKey('home-filter-${filter.name}'),
            container: true,
            button: true,
            selected: isSelected,
            label: 'Filtro ${filter.label}',
            hint: isSelected ? 'Filtro ativo' : 'Toque para filtrar',
            child: InkWell(
              borderRadius: BorderRadius.circular(999),
              onTap: () => onSelected(filter),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: isSelected
                      ? scheme.primary.withValues(alpha: 0.10)
                      : scheme.surface,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: isSelected ? scheme.primary : scheme.outlineVariant,
                  ),
                ),
                child: Center(
                  child: Text(
                    filter.label,
                    style: TextStyle(
                      color:
                          isSelected ? scheme.primary : scheme.onSurfaceVariant,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ),
          );
        },
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemCount: filters.length,
      ),
    );
  }
}
