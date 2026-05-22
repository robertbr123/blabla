import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

class QuickAction {
  const QuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.color,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color color;
}

class QuickActions extends StatelessWidget {
  const QuickActions({super.key, required this.actions});
  final List<QuickAction> actions;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return SizedBox(
      height: 116,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        itemCount: actions.length,
        separatorBuilder: (_, __) =>
            const SizedBox(width: BrandTokens.spaceMd),
        itemBuilder: (_, i) {
          final a = actions[i];
          return _ActionTile(action: a, isDark: isDark);
        },
      ),
    );
  }
}

class _ActionTile extends StatefulWidget {
  const _ActionTile({required this.action, required this.isDark});
  final QuickAction action;
  final bool isDark;

  @override
  State<_ActionTile> createState() => _ActionTileState();
}

class _ActionTileState extends State<_ActionTile> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final a = widget.action;
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      onTap: a.onTap,
      child: AnimatedScale(
        scale: _pressed ? 0.95 : 1.0,
        duration: BrandTokens.motionFast,
        child: Container(
          width: 108,
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: widget.isDark
                ? BrandTokens.surfaceDark
                : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: BrandTokens.elevation1,
            border: Border.all(
              color: widget.isDark
                  ? Colors.white12
                  : BrandTokens.divider.withOpacity(0.6),
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: a.color.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                ),
                child: Icon(a.icon, color: a.color, size: 22),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                a.label,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
