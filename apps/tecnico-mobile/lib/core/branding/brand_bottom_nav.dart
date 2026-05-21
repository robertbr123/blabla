import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Item de navegação para `BrandBottomNav`.
class BrandNavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;

  const BrandNavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}

/// Bottom nav flutuante BlaBla com **pill deslizante**.
///
/// - Todos os itens sempre mostram ícone + label
/// - Uma bolha emerald desliza entre slots com curve "easeOutBack" (bounce sutil)
/// - Selected item: ícone preenchido + texto emerald 600
/// - Unselected: ícone outlined + texto cinza 500
/// - Haptic feedback `selectionClick` na troca
class BrandBottomNav extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final List<BrandNavItem> items;

  const BrandBottomNav({
    super.key,
    required this.selectedIndex,
    required this.onSelect,
    required this.items,
  });

  static const _kHeight = 60.0;
  static const _kRadius = 22.0;
  static const _kSlideDuration = Duration(milliseconds: 420);

  void _handleTap(int i) {
    if (i == selectedIndex) return;
    HapticFeedback.selectionClick();
    onSelect(i);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
        child: Container(
          height: _kHeight,
          decoration: BoxDecoration(
            color: scheme.surfaceContainer,
            borderRadius: BorderRadius.circular(_kRadius),
            border: Border.all(color: scheme.outlineVariant, width: 0.8),
            boxShadow: [
              BoxShadow(
                color: scheme.shadow.withValues(alpha: isDark ? 0.45 : 0.08),
                blurRadius: 24,
                offset: const Offset(0, 10),
                spreadRadius: -2,
              ),
              BoxShadow(
                color: scheme.primary.withValues(alpha: isDark ? 0.12 : 0.06),
                blurRadius: 30,
                offset: const Offset(0, 4),
                spreadRadius: -4,
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(_kRadius),
            child: LayoutBuilder(builder: (context, c) {
              final slotW = c.maxWidth / items.length;
              return Stack(
                children: [
                  // 1) A bolha emerald que desliza
                  AnimatedPositioned(
                    duration: _kSlideDuration,
                    curve: Curves.easeOutBack,
                    left: selectedIndex * slotW + 4,
                    top: 4,
                    bottom: 4,
                    width: slotW - 8,
                    child: AnimatedContainer(
                      duration: _kSlideDuration,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            scheme.primary.withValues(alpha: isDark ? 0.22 : 0.14),
                            scheme.primary.withValues(alpha: isDark ? 0.14 : 0.08),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(_kRadius - 4),
                        border: Border.all(
                          color:
                              scheme.primary.withValues(alpha: isDark ? 0.45 : 0.30),
                          width: 1,
                        ),
                      ),
                    ),
                  ),
                  // 2) Itens (ícone + label) sobre a bolha
                  Row(
                    children: [
                      for (var i = 0; i < items.length; i++)
                        Expanded(
                          child: _NavSlot(
                            item: items[i],
                            selected: i == selectedIndex,
                            onTap: () => _handleTap(i),
                          ),
                        ),
                    ],
                  ),
                ],
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _NavSlot extends StatelessWidget {
  final BrandNavItem item;
  final bool selected;
  final VoidCallback onTap;

  const _NavSlot({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final fg = selected ? scheme.primary : scheme.onSurfaceVariant;

    return Semantics(
      button: true,
      selected: selected,
      label: item.label,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          splashFactory: InkSparkle.splashFactory,
          highlightColor: scheme.primary.withValues(alpha: 0.06),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Ícone faz "pulinho" e troca de variante (outlined → filled) ao selecionar
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 220),
                transitionBuilder: (child, anim) => ScaleTransition(
                  scale: Tween<double>(begin: 0.7, end: 1.0).animate(
                    CurvedAnimation(parent: anim, curve: Curves.easeOutBack),
                  ),
                  child: FadeTransition(opacity: anim, child: child),
                ),
                child: Icon(
                  selected ? item.selectedIcon : item.icon,
                  key: ValueKey<bool>(selected),
                  color: fg,
                  size: selected ? 22 : 21,
                ),
              ),
              const SizedBox(height: 2),
              // Label com transição suave de peso + cor
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOut,
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: fg,
                  letterSpacing: selected ? 0.2 : 0.1,
                ),
                child: Text(
                  item.label,
                  maxLines: 1,
                  overflow: TextOverflow.fade,
                  softWrap: false,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
