import 'package:flutter/material.dart';

/// Design tokens do app do cliente final. Paleta da logo Ondeline:
/// ciano + azul marinho profundo.
class BrandTokens {
  BrandTokens._();

  // Cores principais — derivadas da logo
  static const Color primary = Color(0xFF14B8B0); // Ciano Ondeline
  static const Color primaryDark = Color(0xFF0B1F3A); // Azul marinho fundo da logo
  static const Color accent = Color(0xFF14B8B0);
  static const Color accentDark = Color(0xFF0F8F89);

  // Neutros (light)
  static const Color background = Color(0xFFF4F8FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF0B1F3A);
  static const Color textSecondary = Color(0xFF5B6F8A);
  static const Color divider = Color(0xFFE3EBF0);

  // Neutros (dark) — usa o azul marinho da logo como fundo
  static const Color backgroundDark = Color(0xFF051329);
  static const Color surfaceDark = Color(0xFF0B1F3A);
  static const Color textPrimaryDark = Color(0xFFEFF7F8);
  static const Color textSecondaryDark = Color(0xFF8FA3BD);

  // Status
  static const Color success = Color(0xFF14B8B0);
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
      color: primaryDark.withOpacity(0.10),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
  ];

  static final List<BoxShadow> shadowCard = [
    BoxShadow(
      color: primaryDark.withOpacity(0.05),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];
}
