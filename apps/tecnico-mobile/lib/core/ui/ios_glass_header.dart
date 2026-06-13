import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

/// Barra de topo de vidro estilo iOS 26 — compacta.
/// Use como PRIMEIRO sliver de um CustomScrollView. Fica fixa (pinned), com
/// título e ações na MESMA linha e fundo translúcido que desfoca o conteúdo
/// que rola por baixo. Suporta um subtítulo opcional (segunda linha menor).
///
/// Assume até 2 [actions] à direita. Com 3+, conferir o espaço do título.
class IosGlassHeader extends StatelessWidget {
  const IosGlassHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions = const [],
    this.showBackButton = false,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final bool showBackButton;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return SliverAppBar(
      pinned: true,
      titleSpacing: 16,
      toolbarHeight: subtitle == null ? 56 : 66,
      backgroundColor: scheme.surface.withValues(alpha: 0.7),
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: showBackButton,
      title: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
              color: scheme.onSurface,
            ),
          ),
          if (subtitle != null)
            Text(
              subtitle!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w500,
              ),
            ),
        ],
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
