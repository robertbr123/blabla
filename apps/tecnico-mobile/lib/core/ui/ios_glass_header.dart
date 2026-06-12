import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../branding/brand_theme.dart';

/// Header large-title de vidro estilo iOS 26.
/// Use como PRIMEIRO sliver de um CustomScrollView. O título grande colapsa
/// pro inline ao rolar e o fundo translúcido desfoca o conteúdo por baixo.
class IosGlassHeader extends StatelessWidget {
  const IosGlassHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions = const [],
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return SliverAppBar(
      pinned: true,
      expandedHeight: subtitle == null ? 104 : 120,
      backgroundColor: scheme.surface.withValues(alpha: 0.7),
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      automaticallyImplyLeading: false,
      actions: actions,
      flexibleSpace: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: FlexibleSpaceBar(
            expandedTitleScale: 1.0,
            titlePadding: const EdgeInsetsDirectional.only(
              start: 16,
              bottom: 12,
              end: 72,
            ),
            title: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: iosLargeTitle(scheme)),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12.5,
                      color: scheme.onSurfaceVariant,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
