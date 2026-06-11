import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../branding/brand_tokens.dart';

/// AppBar de vidro (liquid glass): blur do conteúdo que passa por trás +
/// fundo translúcido + linha-brilho na base. Drop-in replacement de AppBar.
/// Usar com `extendBodyBehindAppBar: true` no Scaffold pro blur ter efeito;
/// em scrollables, compensar o topo com
/// `MediaQuery.paddingOf(context).top + kToolbarHeight`.
class GlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  const GlassAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.bottom,
  });

  final String title;
  final List<Widget>? actions;
  final Widget? leading;
  final PreferredSizeWidget? bottom;

  @override
  Size get preferredSize =>
      Size.fromHeight(kToolbarHeight + (bottom?.preferredSize.height ?? 0));

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? BrandTokens.surfaceDark : BrandTokens.background;
    final fg = Theme.of(context).appBarTheme.foregroundColor ??
        Theme.of(context).colorScheme.onSurface;

    return ClipRect(
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: AppBar(
          title: Text(title),
          actions: actions,
          leading: leading,
          bottom: bottom,
          backgroundColor: bg.withValues(alpha: isDark ? 0.55 : 0.62),
          foregroundColor: fg,
          surfaceTintColor: Colors.transparent,
          scrolledUnderElevation: 0,
          elevation: 0,
          shape: Border(
            bottom: BorderSide(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.06)
                  : Colors.white.withValues(alpha: 0.55),
            ),
          ),
        ),
      ),
    );
  }
}
