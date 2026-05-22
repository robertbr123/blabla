import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'brand_tokens.dart';

class BrandTheme {
  BrandTheme._();

  static ThemeData light() {
    final base = ColorScheme.fromSeed(
      seedColor: BrandTokens.primary,
      brightness: Brightness.light,
      primary: BrandTokens.primary,
      secondary: BrandTokens.accent,
      surface: BrandTokens.surface,
      error: BrandTokens.danger,
    );
    return _build(
      base,
      BrandTokens.background,
      BrandTokens.textPrimary,
      BrandTokens.textSecondary,
      BrandTokens.divider,
    );
  }

  static ThemeData dark() {
    final base = ColorScheme.fromSeed(
      seedColor: BrandTokens.primary,
      brightness: Brightness.dark,
      primary: BrandTokens.primary,
      secondary: BrandTokens.accent,
      surface: BrandTokens.surfaceDark,
      error: BrandTokens.danger,
    );
    return _build(
      base,
      BrandTokens.backgroundDark,
      BrandTokens.textPrimaryDark,
      BrandTokens.textSecondaryDark,
      Colors.white12,
    );
  }

  static ThemeData _build(
    ColorScheme scheme,
    Color background,
    Color textPrimary,
    Color textSecondary,
    Color divider,
  ) {
    final textTheme = GoogleFonts.plusJakartaSansTextTheme().apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );

    return ThemeData(
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      textTheme: textTheme,
      useMaterial3: true,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
          textStyle:
              textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd,
          vertical: BrandTokens.spaceMd,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: divider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: divider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: scheme.primary, width: 2),
        ),
      ),
      dividerTheme: DividerThemeData(color: divider, thickness: 1),
    );
  }
}
