import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

/// AppBar de vidro estilo iOS 26 — versão `PreferredSizeWidget`, pra telas que
/// NÃO usam CustomScrollView/sliver (forms, Stepper, etc). Irmão não-sliver do
/// `IosGlassHeader`. Em telas com CustomScrollView, prefira o `IosGlassHeader`.
class IosGlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  const IosGlassAppBar({
    super.key,
    required this.title,
    this.actions = const [],
    this.leading,
    this.showBackButton = true,
  });

  final String title;
  final List<Widget> actions;
  final Widget? leading;
  final bool showBackButton;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    // O blur vai no flexibleSpace do PRÓPRIO AppBar (não num ClipRect externo):
    // assim o AppBar continua sendo quem cuida do inset da status bar e nada é
    // cortado em aparelho com notch. Mesmo padrão do IosGlassHeader (SliverAppBar).
    // Obs: sem `extendBodyBehindAppBar: true` na tela o blur é só translucidez
    // (não há conteúdo rolando atrás) — esperado pra telas de form.
    return AppBar(
      backgroundColor: scheme.surface.withValues(alpha: 0.7),
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: showBackButton,
      leading: leading,
      titleSpacing: 16,
      title: Text(
        title,
        style: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.3,
          color: scheme.onSurface,
        ),
      ),
      actions: actions,
      flexibleSpace: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: const SizedBox.expand(),
        ),
      ),
    );
  }
}
