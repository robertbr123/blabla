import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'brand_tokens.dart';

/// Tema BlaBla — emerald primary + slate neutral + Inter.
/// Alinhado com o dashboard web.
ThemeData buildBrandTheme(Brightness brightness) {
  final isDark = brightness == Brightness.dark;
  final scheme = isDark ? _darkScheme : _lightScheme;
  final tokens = isDark ? BrandTokens.dark : BrandTokens.lightCorrected;

  final baseText = GoogleFonts.interTextTheme(
    isDark ? ThemeData.dark().textTheme : ThemeData.light().textTheme,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surface,
    extensions: [tokens],
    textTheme: baseText.copyWith(
      displayLarge: baseText.displayLarge?.copyWith(fontWeight: FontWeight.w700),
      headlineLarge: baseText.headlineLarge?.copyWith(fontWeight: FontWeight.w700),
      headlineMedium: baseText.headlineMedium?.copyWith(fontWeight: FontWeight.w600),
      titleLarge: baseText.titleLarge?.copyWith(fontWeight: FontWeight.w600),
      titleMedium: baseText.titleMedium?.copyWith(fontWeight: FontWeight.w600),
      labelLarge: baseText.labelLarge?.copyWith(fontWeight: FontWeight.w500),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.surface,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      scrolledUnderElevation: 1,
      centerTitle: false,
      titleTextStyle: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: scheme.onSurface,
      ),
    ),
    cardTheme: CardThemeData(
      color: scheme.surfaceContainer,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: scheme.primary,
        side: BorderSide(color: scheme.outlineVariant),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: scheme.primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerLow,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: scheme.surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: scheme.primary.withValues(alpha: 0.14),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return GoogleFonts.inter(
          fontSize: 11.5,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          color: selected ? scheme.primary : scheme.onSurfaceVariant,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return IconThemeData(color: scheme.primary, size: 24);
        }
        return IconThemeData(color: scheme.onSurfaceVariant, size: 22);
      }),
    ),
  );
}

/// TextStyle helper com tabular nums — pra valores/contadores/coordenadas.
TextStyle tabularStyle(TextStyle? base) {
  return (base ?? const TextStyle()).copyWith(
    fontFeatures: const [FontFeature.tabularFigures()],
  );
}

// ── ColorSchemes ──

const _lightScheme = ColorScheme(
  brightness: Brightness.light,
  primary: Color(0xFF10B981), // emerald-500
  onPrimary: Colors.white,
  primaryContainer: Color(0xFFD1FAE5), // emerald-100
  onPrimaryContainer: Color(0xFF065F46), // emerald-800
  secondary: Color(0xFF0F766E), // teal-700 — complemento
  onSecondary: Colors.white,
  secondaryContainer: Color(0xFFCCFBF1),
  onSecondaryContainer: Color(0xFF134E4A),
  tertiary: Color(0xFF3B82F6),
  onTertiary: Colors.white,
  error: Color(0xFFEF4444),
  onError: Colors.white,
  errorContainer: Color(0xFFFEE2E2),
  onErrorContainer: Color(0xFF7F1D1D),
  surface: Color(0xFFFFFFFF),
  onSurface: Color(0xFF0F172A), // slate-900
  surfaceContainerLowest: Color(0xFFFFFFFF),
  surfaceContainerLow: Color(0xFFF8FAFC), // slate-50
  surfaceContainer: Color(0xFFFFFFFF),
  surfaceContainerHigh: Color(0xFFF1F5F9), // slate-100
  surfaceContainerHighest: Color(0xFFE2E8F0), // slate-200
  onSurfaceVariant: Color(0xFF64748B), // slate-500
  outline: Color(0xFFCBD5E1), // slate-300
  outlineVariant: Color(0xFFE2E8F0), // slate-200
  inverseSurface: Color(0xFF0F172A),
  onInverseSurface: Color(0xFFF8FAFC),
  shadow: Colors.black,
  scrim: Colors.black,
);

const _darkScheme = ColorScheme(
  brightness: Brightness.dark,
  primary: Color(0xFF34D399), // emerald-400 (mais claro p/ contraste no dark)
  onPrimary: Color(0xFF022C22), // emerald-950
  primaryContainer: Color(0xFF065F46),
  onPrimaryContainer: Color(0xFFD1FAE5),
  secondary: Color(0xFF14B8A6),
  onSecondary: Color(0xFF022C22),
  secondaryContainer: Color(0xFF134E4A),
  onSecondaryContainer: Color(0xFFCCFBF1),
  tertiary: Color(0xFF60A5FA),
  onTertiary: Color(0xFF0F172A),
  error: Color(0xFFF87171),
  onError: Color(0xFF7F1D1D),
  errorContainer: Color(0xFF7F1D1D),
  onErrorContainer: Color(0xFFFECACA),
  surface: Color(0xFF0F172A), // slate-900
  onSurface: Color(0xFFF8FAFC),
  surfaceContainerLowest: Color(0xFF0F172A),
  surfaceContainerLow: Color(0xFF111827),
  surfaceContainer: Color(0xFF1E293B), // slate-800
  surfaceContainerHigh: Color(0xFF334155), // slate-700
  surfaceContainerHighest: Color(0xFF475569),
  onSurfaceVariant: Color(0xFF94A3B8), // slate-400
  outline: Color(0xFF475569),
  outlineVariant: Color(0xFF334155),
  inverseSurface: Color(0xFFF8FAFC),
  onInverseSurface: Color(0xFF0F172A),
  shadow: Colors.black,
  scrim: Colors.black,
);
