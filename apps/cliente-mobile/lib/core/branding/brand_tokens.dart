import 'package:flutter/material.dart';

/// Design tokens do app do cliente final. Paleta fintech-style.
class BrandTokens {
  BrandTokens._();

  // Cores principais
  static const Color primary = Color(0xFF3A2A6B); // Roxo profundo
  static const Color primaryDark = Color(0xFF241A47);
  static const Color accent = Color(0xFF1FB378); // Verde-menta
  static const Color accentDark = Color(0xFF158B5A);

  // Neutros (light)
  static const Color background = Color(0xFFF7F6FB);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF1A1430);
  static const Color textSecondary = Color(0xFF6B6480);
  static const Color divider = Color(0xFFEDEAF3);

  // Neutros (dark)
  static const Color backgroundDark = Color(0xFF0F0B1F);
  static const Color surfaceDark = Color(0xFF1A1530);
  static const Color textPrimaryDark = Color(0xFFF5F2FF);
  static const Color textSecondaryDark = Color(0xFF9C95B8);

  // Status
  static const Color success = Color(0xFF1FB378);
  static const Color warning = Color(0xFFE8A33D);
  static const Color danger = Color(0xFFE0455A);
  static const Color info = Color(0xFF3B82F6);

  // Raios
  static const double radiusSm = 12;
  static const double radiusMd = 16;
  static const double radiusLg = 24;
  static const double radiusXl = 32;

  // Espacos
  static const double spaceXs = 4;
  static const double spaceSm = 8;
  static const double spaceMd = 16;
  static const double spaceLg = 24;
  static const double spaceXl = 32;
  static const double spaceXxl = 48;

  // Sombras
  static final List<BoxShadow> shadowSoft = [
    BoxShadow(
      color: primary.withOpacity(0.06),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
  ];

  static final List<BoxShadow> shadowCard = [
    BoxShadow(
      color: primary.withOpacity(0.04),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];
}
