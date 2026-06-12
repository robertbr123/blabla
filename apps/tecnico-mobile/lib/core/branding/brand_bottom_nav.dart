import 'dart:ui' show ImageFilter;
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

/// Bottom nav flutuante BlaBla com **liquid glass**.
///
/// - Todos os itens sempre mostram ícone + label
/// - Uma lente de vidro especular desliza entre slots com curve "easeOutBack" (bounce sutil)
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
  static const _kRadius = 26.0;
  static const _kBlurSigma = 20.0;
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

    // Camadas translúcidas do vidro conforme o tema.
    final glassTop = isDark
        ? const Color(0xFF282E32).withValues(alpha: 0.55)
        : Colors.white.withValues(alpha: 0.55);
    final glassBottom = isDark
        ? const Color(0xFF1C2024).withValues(alpha: 0.42)
        : Colors.white.withValues(alpha: 0.32);
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.14)
        : Colors.white.withValues(alpha: 0.70);

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
        child: DecoratedBox(
          // Sombra externa fica AQUI (fora do ClipRRect — o clip cortaria).
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(_kRadius),
            boxShadow: [
              BoxShadow(
                color: scheme.shadow.withValues(alpha: isDark ? 0.5 : 0.22),
                blurRadius: isDark ? 36 : 34,
                offset: const Offset(0, 12),
                spreadRadius: -2,
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(_kRadius),
            child: BackdropFilter(
              filter:
                  ImageFilter.blur(sigmaX: _kBlurSigma, sigmaY: _kBlurSigma),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [glassTop, glassBottom],
                  ),
                  borderRadius: BorderRadius.circular(_kRadius),
                  border: Border.all(color: borderColor, width: 1),
                ),
                child: SizedBox(
                  height: _kHeight,
                  child: LayoutBuilder(builder: (context, c) {
                    final slotW = c.maxWidth / items.length;
                    return Stack(
                      children: [
                        // Bolha antiga (substituída pela lente na Task 3).
                        AnimatedPositioned(
                          duration: _kSlideDuration,
                          curve: Curves.easeOutBack,
                          left: selectedIndex * slotW + 6,
                          top: 5,
                          bottom: 5,
                          width: slotW - 12,
                          child: AnimatedContainer(
                            duration: _kSlideDuration,
                            decoration: BoxDecoration(
                              color: scheme.primary
                                  .withValues(alpha: isDark ? 0.16 : 0.10),
                              borderRadius: BorderRadius.circular(22),
                            ),
                          ),
                        ),
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
