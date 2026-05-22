import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

/// Item da nav. `badgeCount` > 0 mostra contador; `badgeDot` mostra
/// ponto vermelho sem número.
class FloatingNavItem {
  const FloatingNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    this.badgeCount = 0,
    this.badgeDot = false,
  });
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final int badgeCount;
  final bool badgeDot;
}

/// Barra de navegação flutuante. Pílula com sombra suave, ícone+label
/// animados na seleção, badges por item.
class FloatingNavBar extends StatelessWidget {
  const FloatingNavBar({
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });

  final List<FloatingNavItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark
        ? BrandTokens.surfaceDark
        : BrandTokens.surface;

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          BrandTokens.spaceMd,
          0,
          BrandTokens.spaceMd,
          BrandTokens.spaceMd,
        ),
        child: Container(
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
            boxShadow: BrandTokens.elevation3,
            border: Border.all(
              color: isDark ? Colors.white12 : BrandTokens.divider,
            ),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceSm,
            vertical: BrandTokens.spaceSm,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              for (int i = 0; i < items.length; i++)
                Expanded(
                  child: _NavItemTile(
                    item: items[i],
                    selected: i == currentIndex,
                    onTap: () => onTap(i),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItemTile extends StatelessWidget {
  const _NavItemTile({
    required this.item,
    required this.selected,
    required this.onTap,
  });
  final FloatingNavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final activeColor = BrandTokens.primary;
    final inactiveColor = Theme.of(context).brightness == Brightness.dark
        ? BrandTokens.textSecondaryDark
        : BrandTokens.textSecondary;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: AnimatedContainer(
          duration: BrandTokens.motionMedium,
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceSm,
            vertical: 10,
          ),
          decoration: BoxDecoration(
            gradient: selected
                ? LinearGradient(
                    colors: [
                      activeColor.withOpacity(0.14),
                      activeColor.withOpacity(0.06),
                    ],
                  )
                : null,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _IconWithBadge(
                icon: selected ? item.selectedIcon : item.icon,
                color: selected ? activeColor : inactiveColor,
                badgeCount: item.badgeCount,
                badgeDot: item.badgeDot,
                selected: selected,
              ),
              const SizedBox(height: 4),
              AnimatedDefaultTextStyle(
                duration: BrandTokens.motionFast,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                  color: selected ? activeColor : inactiveColor,
                  letterSpacing: 0.2,
                ),
                child: Text(item.label),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IconWithBadge extends StatelessWidget {
  const _IconWithBadge({
    required this.icon,
    required this.color,
    required this.badgeCount,
    required this.badgeDot,
    required this.selected,
  });
  final IconData icon;
  final Color color;
  final int badgeCount;
  final bool badgeDot;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      height: 26,
      child: Stack(
        clipBehavior: Clip.none,
        alignment: Alignment.center,
        children: [
          AnimatedScale(
            duration: BrandTokens.motionMedium,
            curve: Curves.easeOutBack,
            scale: selected ? 1.12 : 1.0,
            child: Icon(icon, color: color, size: 24),
          ),
          if (badgeCount > 0)
            Positioned(
              top: -4,
              right: 0,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 5,
                  vertical: 1,
                ),
                constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                decoration: BoxDecoration(
                  color: BrandTokens.danger,
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: Theme.of(context).brightness == Brightness.dark
                        ? BrandTokens.surfaceDark
                        : BrandTokens.surface,
                    width: 2,
                  ),
                ),
                child: Text(
                  badgeCount > 9 ? '9+' : '$badgeCount',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    height: 1.0,
                  ),
                ),
              ),
            )
          else if (badgeDot)
            Positioned(
              top: -2,
              right: 2,
              child: Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: BrandTokens.danger,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Theme.of(context).brightness == Brightness.dark
                        ? BrandTokens.surfaceDark
                        : BrandTokens.surface,
                    width: 2,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
