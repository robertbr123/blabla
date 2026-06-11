import 'dart:math' as math;
import 'dart:ui' as ui;

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

/// Barra de navegação flutuante. Pílula com sombra suave e uma "bolha"
/// líquida única que desliza entre os itens na seleção (estilo iOS).
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
    final bg = isDark ? BrandTokens.surfaceDark : BrandTokens.surface;

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          BrandTokens.spaceMd,
          0,
          BrandTokens.spaceMd,
          BrandTokens.spaceMd,
        ),
        // Sombra fica fora do ClipRRect — dentro seria clipada junto com o blur.
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
            boxShadow: BrandTokens.elevation3,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
            child: BackdropFilter(
              filter: ui.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                decoration: BoxDecoration(
                  // Translúcido: o conteúdo desfocado aparece através (liquid glass).
                  color: bg.withValues(alpha: isDark ? 0.55 : 0.62),
                  borderRadius: BorderRadius.circular(BrandTokens.radius2xl),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.10)
                        : Colors.white.withValues(alpha: 0.65),
                    width: 1.2,
                  ),
                ),
                padding: const EdgeInsets.symmetric(
                  horizontal: BrandTokens.spaceSm,
                  vertical: BrandTokens.spaceSm,
                ),
                // Stack: a bolha viaja atrás dos itens (continuidade — um único
                // elemento desliza em vez de sumir/aparecer em cada tile).
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: _NavBubble(
                        currentIndex: currentIndex,
                        itemCount: items.length,
                      ),
                    ),
                    Row(
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
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A bolha líquida. Desliza do slot antigo pro novo (curva iOS) e estica na
/// horizontal no meio do caminho (squash/stretch), deixando um "rastro" no
/// sentido oposto ao movimento, como uma gota.
class _NavBubble extends StatefulWidget {
  const _NavBubble({required this.currentIndex, required this.itemCount});
  final int currentIndex;
  final int itemCount;

  @override
  State<_NavBubble> createState() => _NavBubbleState();
}

class _NavBubbleState extends State<_NavBubble>
    with SingleTickerProviderStateMixin {
  // Curva de drawer do iOS: desliza com desaceleração suave, sem bounce.
  static const _curve = Cubic(0.32, 0.72, 0, 1);
  // Quanto a bolha estica no pico da viagem (0 = só desliza). Calibrável.
  static const _stretch = 0.45;

  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 320),
  )..value = 1.0;

  // Alinhamentos em [-1, 1]. _fromX guarda de onde saiu (pode ser um valor
  // interpolado, se a troca aconteceu no meio de outra animação → retarget
  // suave em vez de pulo).
  late double _fromX = _alignXFor(widget.currentIndex);
  late double _toX = _fromX;
  double _currentX = 0;

  double _alignXFor(int index) {
    if (widget.itemCount <= 1) return 0;
    return -1 + 2 * index / (widget.itemCount - 1);
  }

  @override
  void initState() {
    super.initState();
    _currentX = _fromX;
  }

  @override
  void didUpdateWidget(covariant _NavBubble old) {
    super.didUpdateWidget(old);
    if (old.currentIndex != widget.currentIndex) {
      _fromX = _currentX; // posição atual (mesmo se a anterior não terminou)
      _toX = _alignXFor(widget.currentIndex);
      _c.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    const primary = BrandTokens.primary;

    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = _c.value;
        final curved = _curve.transform(t);
        final x = _fromX + (_toX - _fromX) * curved;
        _currentX = x;

        // sin(pi*t): 0 nas pontas, pico no meio → estica e volta.
        final wave = math.sin(math.pi * t);
        final scaleX = 1 + _stretch * wave;
        final scaleY = 1 - 0.12 * wave; // achata de leve (gota)
        // Ancora o stretch no sentido do movimento → rastro pra trás.
        final dir = (_toX - _fromX).sign;

        return Align(
          alignment: Alignment(x, 0),
          child: FractionallySizedBox(
            widthFactor: 1 / widget.itemCount,
            heightFactor: 1,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              child: Transform.scale(
                scaleX: scaleX,
                scaleY: scaleY,
                alignment: Alignment(dir, 0),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        primary.withValues(alpha: isDark ? 0.26 : 0.16),
                        primary.withValues(alpha: isDark ? 0.12 : 0.06),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                  ),
                  child: DecoratedBox(
                    // Specular highlight: faixa de luz no topo da bolha,
                    // simulando vidro refratando a luz ambiente.
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.white.withValues(alpha: isDark ? 0.10 : 0.35),
                          Colors.white.withValues(alpha: 0.0),
                        ],
                        stops: const [0.0, 0.55],
                      ),
                      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
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
    const activeColor = BrandTokens.primary;
    final inactiveColor = Theme.of(context).brightness == Brightness.dark
        ? BrandTokens.textSecondaryDark
        : BrandTokens.textSecondary;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceSm,
            vertical: 10,
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
