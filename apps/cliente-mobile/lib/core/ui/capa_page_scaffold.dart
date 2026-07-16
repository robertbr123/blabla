import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';
import 'capa_folha.dart';

/// Scaffold padrão das telas empurradas na identidade vibrante:
/// capa ciano compacta (voltar + título + ações + slot opcional) e
/// folha clara com o conteúdo. Substitui o GlassAppBar.
class CapaPageScaffold extends StatelessWidget {
  const CapaPageScaffold({
    super.key,
    required this.title,
    this.actions = const [],
    this.capaBottom,
    required this.child,
    this.folhaPadding,
  });

  final String title;
  final List<Widget> actions;

  /// Slot opcional na capa abaixo da linha do título (ex: TabBar, chips).
  final Widget? capaBottom;

  /// Conteúdo da folha (geralmente um scrollável).
  final Widget child;

  /// Padding da folha; default zero (o conteúdo cuida do próprio padding).
  final EdgeInsetsGeometry? folhaPadding;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final canPop = Navigator.of(context).canPop();
    return Scaffold(
      backgroundColor:
          isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Stack(
            children: [
              CapaBackground(
                padding: EdgeInsets.fromLTRB(
                  BrandTokens.spaceMd,
                  MediaQuery.paddingOf(context).top + BrandTokens.spaceSm,
                  BrandTokens.spaceMd,
                  capaBottom != null
                      ? BrandTokens.spaceSm + BrandTokens.radiusFolha
                      : BrandTokens.spaceLg + BrandTokens.radiusFolha,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    IconTheme.merge(
                      data: const IconThemeData(color: BrandTokens.capaInk),
                      child: Row(
                        children: [
                          if (canPop)
                            IconButton(
                              icon: const Icon(Icons.arrow_back_rounded),
                              onPressed: () => Navigator.of(context).pop(),
                            )
                          else
                            const SizedBox(width: BrandTokens.spaceSm),
                          Expanded(
                            child: Text(
                              title,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: BrandTokens.capaInk,
                                fontSize: 24,
                                fontWeight: FontWeight.w900,
                                letterSpacing: -0.6,
                              ),
                            ),
                          ),
                          ...actions,
                        ],
                      ),
                    ),
                    if (capaBottom != null) ...[
                      const SizedBox(height: BrandTokens.spaceSm),
                      capaBottom!,
                    ],
                  ],
                ),
              ),
              const Positioned(left: 0, right: 0, bottom: 0, child: FolhaLip()),
            ],
          ),
          Expanded(
            child: Container(
              color:
                  isDark ? BrandTokens.backgroundDark : BrandTokens.background,
              padding: folhaPadding ?? EdgeInsets.zero,
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}
