import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';
import 'capa_folha.dart';

/// Scaffold compartilhado pelas telas de auth (login, onboarding).
/// Identidade "capa + folha": capa ciano com título/subtítulo no topo,
/// folha clara rolável embaixo com o formulário e os CTAs.
class AuthScaffold extends StatelessWidget {
  const AuthScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.icon = Icons.wifi_rounded,
    this.showBack = false,
    this.bottom,
  });

  final String title;
  final String subtitle;
  final Widget child;

  /// Mantido pela API por compatibilidade com as telas existentes; a capa
  /// vibrante não exibe ícone no header (ver [CapaBackground]). Aceito e
  /// ignorado no build.
  final IconData icon;
  final bool showBack;

  /// CTAs de rodapé (ex: botão principal + link secundário). Renderizado
  /// dentro da folha, logo após [child], já que a folha é rolável.
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      resizeToAvoidBottomInset: true,
      body: GestureDetector(
        onTap: () => FocusScope.of(context).unfocus(),
        behavior: HitTestBehavior.translucent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Capa vibrante com voltar (opcional) + título + subtítulo ──
            CapaBackground(
              padding: EdgeInsets.only(
                left: BrandTokens.spaceLg,
                right: BrandTokens.spaceLg,
                top: MediaQuery.paddingOf(context).top + BrandTokens.spaceLg,
                bottom: BrandTokens.spaceXl,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (showBack) ...[
                    IconButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(
                        Icons.arrow_back_rounded,
                        color: BrandTokens.capaInk,
                      ),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                    const SizedBox(height: BrandTokens.spaceMd),
                  ],
                  Text(
                    title,
                    style: const TextStyle(
                      color: BrandTokens.capaInk,
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.6,
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceXs),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: BrandTokens.capaInk.withValues(alpha: 0.7),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            // ── Folha com o formulário + CTAs ──
            Expanded(
              child: SingleChildScrollView(
                child: FolhaContainer(
                  overlap: BrandTokens.radiusFolha,
                  padding: EdgeInsets.fromLTRB(
                    BrandTokens.spaceLg,
                    BrandTokens.spaceLg,
                    BrandTokens.spaceLg,
                    MediaQuery.paddingOf(context).bottom + BrandTokens.spaceLg,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      child,
                      if (bottom != null) ...[
                        const SizedBox(height: BrandTokens.spaceLg),
                        bottom!,
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
