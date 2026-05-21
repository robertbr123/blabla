import 'package:flutter/material.dart';

import '../../core/branding/brand_empty_state.dart';
import '../../core/branding/brand_kpi_card.dart';
import '../../core/branding/brand_status_pill.dart';
import '../../core/branding/brand_theme.dart';
import '../../core/branding/brand_tokens.dart';

/// Tela de preview do novo design system (Fase 1).
/// Aplica o tema BlaBla SOMENTE nesta rota — sem afetar telas reais.
class DesignPreviewScreen extends StatefulWidget {
  const DesignPreviewScreen({super.key});

  @override
  State<DesignPreviewScreen> createState() => _DesignPreviewScreenState();
}

class _DesignPreviewScreenState extends State<DesignPreviewScreen> {
  Brightness _brightness = Brightness.light;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: buildBrandTheme(_brightness),
      child: Builder(
        builder: (ctx) {
          final scheme = Theme.of(ctx).colorScheme;
          final isDark = _brightness == Brightness.dark;
          return Scaffold(
            backgroundColor: scheme.surface,
            appBar: AppBar(
              title: const Text('Design Preview'),
              actions: [
                IconButton(
                  icon: Icon(isDark ? Icons.light_mode : Icons.dark_mode),
                  tooltip: isDark ? 'Light' : 'Dark',
                  onPressed: () => setState(() {
                    _brightness = isDark ? Brightness.light : Brightness.dark;
                  }),
                ),
              ],
            ),
            body: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  'Fase 1 · Design System BlaBla',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.6,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'BlaBla técnico',
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    color: scheme.onSurface,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Tokens escopados nesta rota. Nenhuma tela real foi modificada.',
                  style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
                ),

                const SizedBox(height: 24),
                _SectionLabel('Paleta semântica'),
                const SizedBox(height: 8),
                _SwatchGrid(brightness: _brightness),

                const SizedBox(height: 24),
                _SectionLabel('Tipografia · Inter'),
                const SizedBox(height: 8),
                _TypographySample(),

                const SizedBox(height: 24),
                _SectionLabel('Status pills · OS'),
                const SizedBox(height: 8),
                Text(
                  'Sempre ícone + texto. Cor sozinha não comunica (a11y · WCAG).',
                  style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
                ),
                const SizedBox(height: 12),
                const Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    BrandStatusPill(label: 'Pendente', icon: Icons.schedule, tone: BrandTone.info),
                    BrandStatusPill(label: 'Em andamento', icon: Icons.play_circle_outline, tone: BrandTone.warning),
                    BrandStatusPill(label: 'Concluída', icon: Icons.check_circle_outline, tone: BrandTone.success),
                    BrandStatusPill(label: 'Cancelada', icon: Icons.cancel_outlined, tone: BrandTone.danger),
                    BrandStatusPill(label: 'Encerrada', icon: Icons.lock_outline, tone: BrandTone.neutral),
                  ],
                ),

                const SizedBox(height: 24),
                _SectionLabel('KPI cards'),
                const SizedBox(height: 8),
                Row(
                  children: const [
                    Expanded(child: BrandKpiCard(label: 'OS abertas', value: '24', icon: Icons.build, tone: BrandTone.warning)),
                    SizedBox(width: 12),
                    Expanded(child: BrandKpiCard(label: 'Concluídas hoje', value: '18', icon: Icons.check_circle_outline, tone: BrandTone.success)),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: const [
                    Expanded(child: BrandKpiCard(label: 'Materiais', value: '1.247', icon: Icons.inventory_2_outlined, tone: BrandTone.info)),
                    SizedBox(width: 12),
                    Expanded(child: BrandKpiCard(label: 'CSAT 30d', value: '4,8', icon: Icons.star_outline, tone: BrandTone.success)),
                  ],
                ),

                const SizedBox(height: 24),
                _SectionLabel('Botões'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton(onPressed: () {}, child: const Text('Iniciar OS')),
                    OutlinedButton(onPressed: () {}, child: const Text('Reatribuir')),
                    TextButton(onPressed: () {}, child: const Text('Ghost')),
                    FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: scheme.error, foregroundColor: scheme.onError),
                      onPressed: () {},
                      child: const Text('Cancelar OS'),
                    ),
                  ],
                ),

                const SizedBox(height: 24),
                _SectionLabel('Input'),
                const SizedBox(height: 8),
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Buscar cliente',
                    hintText: 'Nome, CPF, endereço…',
                    prefixIcon: Icon(Icons.search),
                  ),
                ),

                const SizedBox(height: 24),
                _SectionLabel('Empty state'),
                const SizedBox(height: 8),
                Container(
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: scheme.outlineVariant),
                  ),
                  child: BrandEmptyState(
                    icon: Icons.inbox_outlined,
                    title: 'Nenhuma OS por aqui',
                    description: 'Quando o despachante atribuir uma OS, ela aparece nesta lista.',
                    action: FilledButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('Atualizar'),
                    ),
                  ),
                ),

                const SizedBox(height: 24),
                _SectionLabel('Item de lista (exemplo de OS)'),
                const SizedBox(height: 8),
                _OsListTilePreview(),

                const SizedBox(height: 32),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainer,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: scheme.outlineVariant),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.trending_up, size: 16, color: scheme.onSurfaceVariant),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Aprovado? Próximo passo é promover esses tokens pro theme.dart global.',
                          style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Text(
      text,
      style: TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: scheme.onSurface,
      ),
    );
  }
}

class _SwatchGrid extends StatelessWidget {
  final Brightness brightness;
  const _SwatchGrid({required this.brightness});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final brand = context.brand;
    final swatches = <(String, Color, Color)>[
      ('Primary', scheme.primary, scheme.onPrimary),
      ('Success', brand.success, Colors.white),
      ('Warning', brand.warning, Colors.white),
      ('Info', brand.info, Colors.white),
      ('Danger', brand.danger, Colors.white),
      ('Surface', scheme.surfaceContainer, scheme.onSurface),
      ('Muted', scheme.onSurfaceVariant, scheme.surface),
      ('Outline', scheme.outlineVariant, scheme.onSurface),
    ];

    return GridView.count(
      crossAxisCount: 4,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      childAspectRatio: 1.4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: swatches.map((s) {
        final (name, bg, fg) = s;
        return Container(
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: scheme.outlineVariant),
          ),
          padding: const EdgeInsets.all(8),
          alignment: Alignment.bottomLeft,
          child: Text(
            name,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: fg,
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _TypographySample extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    const samples = [
      ('display · 26/700', 'BlaBla técnico', TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
      ('h1 · 22/600', 'Ordens de serviço', TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
      ('h2 · 16/600', 'Em andamento · 3', TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
      ('body · 14/400', 'João Silva concluiu a OS #1247.', TextStyle(fontSize: 14)),
      ('caption · 12/400', 'Há 2 minutos', TextStyle(fontSize: 12)),
    ];
    return Container(
      decoration: BoxDecoration(
        color: scheme.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Column(
        children: [
          for (final s in samples) ...[
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 110,
                    child: Text(
                      s.$1,
                      style: TextStyle(
                        fontSize: 10,
                        letterSpacing: 0.5,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                  Expanded(child: Text(s.$2, style: s.$3.copyWith(color: scheme.onSurface))),
                ],
              ),
            ),
            if (s != samples.last) Divider(height: 1, color: scheme.outlineVariant),
          ],
          Divider(height: 1, color: scheme.outlineVariant),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                SizedBox(
                  width: 110,
                  child: Text(
                    'tabular · numbers',
                    style: TextStyle(fontSize: 10, letterSpacing: 0.5, color: scheme.onSurfaceVariant),
                  ),
                ),
                Expanded(
                  child: Text(
                    'R\$ 12.480,00  ·  1.247 itens  ·  98,4%',
                    style: tabularStyle(TextStyle(fontSize: 14, color: scheme.onSurface)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OsListTilePreview extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        color: scheme.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant),
      ),
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: context.brand.warningBg,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(Icons.build, size: 18, color: context.brand.warning),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      '#1247',
                      style: tabularStyle(TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: scheme.primary,
                      )),
                    ),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        'Maria Silva',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  'Rua Senador, 438 · Itamarati/AM',
                  style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          const BrandStatusPill(
            label: 'Em andamento',
            icon: Icons.play_circle_outline,
            tone: BrandTone.warning,
            size: BrandPillSize.sm,
          ),
        ],
      ),
    );
  }
}
