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

/// Localiza o artigo + categoria pai a partir do id.
({FaqCategoria? categoria, FaqArtigo? artigo}) _find(String id) {
  for (final c in faqCategorias) {
    for (final a in c.artigos) {
      if (a.id == id) return (categoria: c, artigo: a);
    }
  }
  return (categoria: null, artigo: null);
}

class FaqArtigoScreen extends StatelessWidget {
  const FaqArtigoScreen({super.key, required this.artigoId});
  final String artigoId;

  @override
  Widget build(BuildContext context) {
    final found = _find(artigoId);
    final cat = found.categoria;
    final a = found.artigo;
    if (cat == null || a == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Artigo')),
        body: const Center(child: Text('Artigo nao encontrado.')),
      );
    }
    final color = _catColors[cat.id] ?? BrandTokens.primary;
    return Scaffold(
      appBar: AppBar(
        title: const Text(''),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        children: [
          // Categoria pill
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: 6,
            ),
            decoration: BoxDecoration(
              color: color.withOpacity(0.14),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  cat.titulo.toUpperCase(),
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w800,
                    fontSize: 11,
                    letterSpacing: 1.2,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Text(
            a.titulo,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
          ),
          const SizedBox(height: BrandTokens.spaceSm),
          Text(
            a.resumo,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: BrandTokens.textSecondary,
                ),
          ),
          const SizedBox(height: BrandTokens.spaceLg),
          ...a.passos.map(_paragraph),
          const SizedBox(height: BrandTokens.spaceXl),

          // CTA: ainda precisa de ajuda?
          Container(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            decoration: BoxDecoration(
              color: color.withOpacity(0.08),
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              border: Border.all(color: color.withOpacity(0.25)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Icon(Icons.support_agent_rounded, color: color),
                    const SizedBox(width: BrandTokens.spaceSm),
                    const Expanded(
                      child: Text(
                        'Ainda precisa de ajuda?',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: BrandTokens.spaceXs),
                Text(
                  'Nosso time esta disponivel pra te atender.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: BrandTokens.textSecondary,
                      ),
                ),
                const SizedBox(height: BrandTokens.spaceMd),
                FilledButton.icon(
                  icon: const Icon(Icons.message_outlined, size: 18),
                  label: const Text('Abrir chamado'),
                  onPressed: () => context.push('/suporte/novo'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _paragraph(String texto) {
    final isBullet = texto.startsWith('•') || texto.startsWith('-');
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isBullet) ...[
            const Padding(
              padding: EdgeInsets.only(top: 6, right: 8),
              child: Icon(
                Icons.fiber_manual_record,
                size: 6,
                color: BrandTokens.textSecondary,
              ),
            ),
          ],
          Expanded(
            child: Text(
              isBullet ? texto.substring(1).trim() : texto,
              style: const TextStyle(
                fontSize: 14.5,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
