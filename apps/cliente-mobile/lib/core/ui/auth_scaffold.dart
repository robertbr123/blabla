import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';
import 'animated_gradient_background.dart';

/// Scaffold compartilhado pelas telas de auth (login, onboarding).
/// Mantém visual consistente: fundo animado, header com ícone, título,
/// subtítulo, conteúdo central e CTAs no rodapé.
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
  final IconData icon;
  final bool showBack;
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: BrandTokens.primaryDark,
      body: AnimatedGradientBackground(
        child: SafeArea(
          child: GestureDetector(
            onTap: () => FocusScope.of(context).unfocus(),
            behavior: HitTestBehavior.translucent,
            child: Column(
              children: [
                if (showBack)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Padding(
                      padding: const EdgeInsets.only(
                        left: BrandTokens.spaceSm,
                        top: BrandTokens.spaceSm,
                      ),
                      child: IconButton(
                        icon: const Icon(
                          Icons.arrow_back_ios_new_rounded,
                          color: Colors.white,
                        ),
                        onPressed: () => Navigator.of(context).maybePop(),
                      ),
                    ),
                  ),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(
                      horizontal: BrandTokens.spaceLg,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: BrandTokens.spaceLg),
                        Center(
                          child: Container(
                            width: 72,
                            height: 72,
                            decoration: BoxDecoration(
                              gradient: BrandTokens.gradientPrimary,
                              borderRadius: BorderRadius.circular(
                                  BrandTokens.radiusLg),
                              boxShadow: BrandTokens.shadowColored,
                            ),
                            child: Icon(icon,
                                color: Colors.white, size: 38),
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceLg),
                        Text(
                          title,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 28,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceXs),
                        Text(
                          subtitle,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceXl),
                        child,
                        const SizedBox(height: BrandTokens.spaceLg),
                      ],
                    ),
                  ),
                ),
                if (bottom != null)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      BrandTokens.spaceLg,
                      0,
                      BrandTokens.spaceLg,
                      BrandTokens.spaceMd,
                    ),
                    child: bottom!,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
