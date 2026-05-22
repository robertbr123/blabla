import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/branding/brand_tokens.dart';
import 'faq_data.dart';

const _catColors = <String, Color>{
  'conexao': BrandTokens.catConnection,
  'faturas': BrandTokens.catBilling,
  'conta': BrandTokens.catSupport,
  'plano': BrandTokens.catPlan,
};

const _catIcons = <String, IconData>{
  'wifi': Icons.wifi_rounded,
  'payment': Icons.payments_rounded,
  'account': Icons.person_rounded,
  'speed': Icons.speed_rounded,
};

class FaqScreen extends StatefulWidget {
  const FaqScreen({super.key});

  @override
  State<FaqScreen> createState() => _FaqScreenState();
}

class _FaqScreenState extends State<FaqScreen> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  List<FaqCategoria> get _filtradas {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return faqCategorias;
    return faqCategorias
        .map((c) {
          final artigos = c.artigos
              .where(
                (a) =>
                    a.titulo.toLowerCase().contains(q) ||
                    a.resumo.toLowerCase().contains(q),
              )
              .toList();
          return FaqCategoria(
            id: c.id,
            titulo: c.titulo,
            icon: c.icon,
            artigos: artigos,
          );
        })
        .where((c) => c.artigos.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final cats = _filtradas;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Perguntas frequentes'),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Barra de busca
          Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            child: TextField(
              controller: _searchCtrl,
              onChanged: (v) => setState(() => _query = v),
              decoration: InputDecoration(
                hintText: 'Buscar...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _query.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.close_rounded),
                        onPressed: () {
                          _searchCtrl.clear();
                          setState(() => _query = '');
                        },
                      ),
              ),
            ),
          ),
          Expanded(
            child: cats.isEmpty
                ? _Empty(query: _query)
                : ListView(
                    padding: const EdgeInsets.fromLTRB(
                      BrandTokens.spaceLg,
                      0,
                      BrandTokens.spaceLg,
                      BrandTokens.spaceXl,
                    ),
                    children: [
                      for (final c in cats) _CategoriaCard(categoria: c),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _CategoriaCard extends StatelessWidget {
  const _CategoriaCard({required this.categoria});
  final FaqCategoria categoria;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final color =
        _catColors[categoria.id] ?? BrandTokens.primary;
    final icon = _catIcons[categoria.icon] ?? Icons.help_outline;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(
              left: BrandTokens.spaceXs,
              bottom: BrandTokens.spaceSm,
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.14),
                    borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                  ),
                  child: Icon(icon, color: color, size: 16),
                ),
                const SizedBox(width: BrandTokens.spaceSm),
                Text(
                  categoria.titulo,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
          ),
          Container(
            decoration: BoxDecoration(
              color: isDark
                  ? BrandTokens.surfaceDark
                  : BrandTokens.surface,
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              border: Border.all(
                color: isDark ? Colors.white12 : BrandTokens.divider,
              ),
              boxShadow: BrandTokens.elevation1,
            ),
            child: Column(
              children: [
                for (int i = 0; i < categoria.artigos.length; i++) ...[
                  _ArtigoTile(
                    artigo: categoria.artigos[i],
                    categoriaTitulo: categoria.titulo,
                    color: color,
                  ),
                  if (i < categoria.artigos.length - 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: BrandTokens.spaceMd,
                      ),
                      child: Divider(
                        height: 1,
                        color: isDark ? Colors.white10 : BrandTokens.divider,
                      ),
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ArtigoTile extends StatelessWidget {
  const _ArtigoTile({
    required this.artigo,
    required this.categoriaTitulo,
    required this.color,
  });
  final FaqArtigo artigo;
  final String categoriaTitulo;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: InkWell(
        onTap: () => context.push('/faq/${artigo.id}'),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      artigo.titulo,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      artigo.resumo,
                      style: const TextStyle(
                        color: BrandTokens.textSecondary,
                        fontSize: 12,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.chevron_right_rounded,
                color: BrandTokens.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.query});
  final String query;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceXl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.search_off_rounded,
              size: 48,
              color: BrandTokens.textSecondary,
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              'Nada encontrado pra "$query"',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: BrandTokens.spaceXs),
            const Text(
              'Tente outras palavras ou abra um chamado.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
