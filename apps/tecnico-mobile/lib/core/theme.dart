import 'package:flutter/material.dart';

// Brand colors — derivadas do logo BlaBla (balões verdes + ink navy).
const brandGreen = Color(0xFF16a34a);      // verde principal (balão escuro)
const brandGreenLight = Color(0xFF22c55e); // verde claro (balão da frente)
const brandInk = Color(0xFF0E1729);        // navy do icone
const brandCream = Color(0xFFF8F5EE);      // cream do bg light

// Compat com nomes antigos (alguns widgets ainda referenciam).
const brandBlue = brandGreen;
const brandCyan = brandGreenLight;
const brandBlueDark = Color(0xFF4ade80);
const brandCyanDark = Color(0xFF34d399);

ThemeData buildLightTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: brandGreen,
    onPrimary: Colors.white,
    primaryContainer: Color(0xFFdcfce7),
    onPrimaryContainer: Color(0xFF14532d),
    secondary: brandGreenLight,
    onSecondary: Colors.white,
    secondaryContainer: Color(0xFFd1fae5),
    onSecondaryContainer: Color(0xFF065f46),
    tertiary: Color(0xFF8b5cf6),
    onTertiary: Colors.white,
    error: Color(0xFFdc2626),
    onError: Colors.white,
    errorContainer: Color(0xFFfee2e2),
    onErrorContainer: Color(0xFF7f1d1d),
    surface: Color(0xFFffffff),
    onSurface: Color(0xFF0f172a),
    surfaceContainerLowest: Color(0xFFfafafa),
    surfaceContainerLow: Color(0xFFf8fafc),
    surfaceContainer: Color(0xFFf1f5f9),
    surfaceContainerHigh: Color(0xFFe2e8f0),
    surfaceContainerHighest: Color(0xFFcbd5e1),
    onSurfaceVariant: Color(0xFF475569),
    outline: Color(0xFFcbd5e1),
    outlineVariant: Color(0xFFe2e8f0),
    inverseSurface: Color(0xFF0f172a),
    onInverseSurface: Color(0xFFf1f5f9),
    shadow: Colors.black,
    scrim: Colors.black,
  );

  return _build(scheme);
}

ThemeData buildDarkTheme() {
  // Paleta navy-tinted (espelha o brandInk do icone do app).
  const scheme = ColorScheme(
    brightness: Brightness.dark,
    primary: brandBlueDark,
    onPrimary: Color(0xFF052e16),
    primaryContainer: Color(0xFF14532d),
    onPrimaryContainer: Color(0xFFdcfce7),
    secondary: brandCyanDark,
    onSecondary: Color(0xFF064e3b),
    secondaryContainer: Color(0xFF065f46),
    onSecondaryContainer: Color(0xFFd1fae5),
    tertiary: Color(0xFFa78bfa),
    onTertiary: Color(0xFF2e1065),
    error: Color(0xFFf87171),
    onError: Color(0xFF450a0a),
    errorContainer: Color(0xFF7f1d1d),
    onErrorContainer: Color(0xFFfecaca),
    surface: brandInk,
    onSurface: Color(0xFFf1f5f9),
    surfaceContainerLowest: Color(0xFF070d18),
    surfaceContainerLow: Color(0xFF0c1424),
    surfaceContainer: Color(0xFF1e293b),
    surfaceContainerHigh: Color(0xFF293548),
    surfaceContainerHighest: Color(0xFF334155),
    onSurfaceVariant: Color(0xFF94a3b8),
    outline: Color(0xFF475569),
    outlineVariant: Color(0xFF334155),
    inverseSurface: Color(0xFFf1f5f9),
    onInverseSurface: Color(0xFF0f172a),
    shadow: Colors.black,
    scrim: Colors.black,
  );

  return _build(scheme);
}

ThemeData _build(ColorScheme scheme) {
  return ThemeData(
    useMaterial3: true,
    brightness: scheme.brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: scheme.surfaceContainerLowest,
    appBarTheme: AppBarTheme(
      backgroundColor: scheme.surface,
      foregroundColor: scheme.onSurface,
      centerTitle: false,
      elevation: 0,
      scrolledUnderElevation: 1,
      surfaceTintColor: scheme.surface,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: scheme.surface,
      indicatorColor: scheme.primary
          .withValues(alpha: scheme.brightness == Brightness.dark ? 0.18 : 0.12),
      labelTextStyle: WidgetStateProperty.all(
        const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.primary, width: 1.5),
      ),
    ),
  );
}
