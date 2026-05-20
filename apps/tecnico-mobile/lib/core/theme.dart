import 'package:flutter/material.dart';

const brandCommand = Color(0xFF17324D);
const brandCommandLight = Color(0xFF395572);
const brandAccent = Color(0xFFC18A2D);
const brandAccentSoft = Color(0xFFE6C98B);
const brandWarm = Color(0xFFF6F1E8);
const brandSurface = Color(0xFFFFFCF8);
const brandSurfaceHigh = Color(0xFFEFE7DA);
const brandLine = Color(0xFFD7CCBC);
const brandSuccess = Color(0xFF2E7D5B);
const brandDanger = Color(0xFFB04A3A);

// Legacy aliases kept for existing screens that still import old names.
const brandGreen = brandAccent;
const brandGreenLight = brandAccentSoft;
const brandInk = brandCommand;
const brandCream = brandWarm;
const brandBlue = brandCommand;
const brandCyan = brandCommandLight;
const brandBlueDark = Color(0xFF7FA4C5);
const brandCyanDark = Color(0xFFAFC7DE);

ThemeData buildLightTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: brandCommand,
    onPrimary: Colors.white,
    primaryContainer: Color(0xFFD9E4EF),
    onPrimaryContainer: Color(0xFF0C2135),
    secondary: brandAccent,
    onSecondary: Color(0xFF2F2310),
    secondaryContainer: Color(0xFFF1DFC0),
    onSecondaryContainer: Color(0xFF4B390D),
    tertiary: brandSuccess,
    onTertiary: Colors.white,
    error: brandDanger,
    onError: Colors.white,
    errorContainer: Color(0xFFF4D8D2),
    onErrorContainer: Color(0xFF5D251B),
    surface: brandSurface,
    onSurface: Color(0xFF182432),
    surfaceContainerLowest: brandWarm,
    surfaceContainerLow: Color(0xFFFBF7F0),
    surfaceContainer: Color(0xFFF7F1E7),
    surfaceContainerHigh: brandSurfaceHigh,
    surfaceContainerHighest: Color(0xFFE6DCCF),
    onSurfaceVariant: Color(0xFF5A6572),
    outline: Color(0xFFB4A99A),
    outlineVariant: brandLine,
    inverseSurface: Color(0xFF132030),
    onInverseSurface: Color(0xFFF7F1E7),
    shadow: Colors.black,
    scrim: Colors.black,
  );

  return _build(scheme);
}

ThemeData buildDarkTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.dark,
    primary: brandBlueDark,
    onPrimary: Color(0xFF0E2135),
    primaryContainer: Color(0xFF1E3854),
    onPrimaryContainer: Color(0xFFD9E4EF),
    secondary: brandCyanDark,
    onSecondary: Color(0xFF2F2310),
    secondaryContainer: Color(0xFF70531D),
    onSecondaryContainer: Color(0xFFF4E5C9),
    tertiary: Color(0xFF73BC97),
    onTertiary: Color(0xFF092B1E),
    error: Color(0xFFF0A292),
    onError: Color(0xFF4E180F),
    errorContainer: Color(0xFF6E2E23),
    onErrorContainer: Color(0xFFF7DDD7),
    surface: Color(0xFF0E1724),
    onSurface: Color(0xFFF6EFE4),
    surfaceContainerLowest: Color(0xFF09111B),
    surfaceContainerLow: Color(0xFF101C2A),
    surfaceContainer: Color(0xFF152231),
    surfaceContainerHigh: Color(0xFF1B2A3D),
    surfaceContainerHighest: Color(0xFF253852),
    onSurfaceVariant: Color(0xFFB9C2CC),
    outline: Color(0xFF5D7087),
    outlineVariant: Color(0xFF30445C),
    inverseSurface: Color(0xFFF6EFE4),
    onInverseSurface: Color(0xFF102030),
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
      backgroundColor: scheme.surfaceContainerLowest,
      foregroundColor: scheme.onSurface,
      centerTitle: false,
      elevation: 0,
      scrolledUnderElevation: 1,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(
        color: scheme.onSurface,
        fontSize: 22,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(48),
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.1,
        ),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: scheme.surface,
      selectedColor: scheme.primaryContainer,
      side: BorderSide(color: scheme.outlineVariant),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      labelStyle: TextStyle(
        color: scheme.onSurface,
        fontSize: 12,
        fontWeight: FontWeight.w600,
      ),
    ),
    cardTheme: CardThemeData(
      color: scheme.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shadowColor: Colors.black.withValues(alpha: 0.05),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.65)),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: scheme.surface,
      indicatorColor: scheme.primary.withValues(
        alpha: scheme.brightness == Brightness.dark ? 0.22 : 0.10,
      ),
      labelTextStyle: WidgetStateProperty.all(
        const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: scheme.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
  );
}
