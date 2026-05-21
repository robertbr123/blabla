import 'package:flutter/material.dart';

/// Tokens semânticos da marca BlaBla. Espelha os tokens do dashboard
/// (`--success`, `--warning`, `--info`, `--destructive` etc).
///
/// Uso: `Theme.of(context).extension<BrandTokens>()!.success`.
@immutable
class BrandTokens extends ThemeExtension<BrandTokens> {
  // Emerald é a marca (logo BlaBla).
  static const Color emerald500 = Color(0xFF10B981);
  static const Color emerald600 = Color(0xFF059669);
  static const Color emerald400 = Color(0xFF34D399);

  // Semantic
  static const Color successLight = Color(0xFF10B981);
  static const Color successDark = Color(0xFF34D399);
  static const Color warningLight = Color(0xFFF59E0B);
  static const Color warningDark = Color(0xFFFBBF24);
  static const Color infoLight = Color(0xFF3B82F6);
  static const Color infoDark = Color(0xFF60A5FA);
  static const Color dangerLight = Color(0xFFEF4444);
  static const Color dangerDark = Color(0xFFF87171);

  final Color success;
  final Color warning;
  final Color info;
  final Color danger;

  /// Tonal background do mesmo tom (≈ 12-15% opacity da cor sólida em light).
  final Color successBg;
  final Color warningBg;
  final Color infoBg;
  final Color dangerBg;

  /// Cor pra texto sobre as cores sólidas (sempre branco aqui — emerald/blue/amber/red são saturados).
  final Color onSemantic;

  const BrandTokens({
    required this.success,
    required this.warning,
    required this.info,
    required this.danger,
    required this.successBg,
    required this.warningBg,
    required this.infoBg,
    required this.dangerBg,
    required this.onSemantic,
  });

  static const BrandTokens light = BrandTokens(
    success: successLight,
    warning: warningLight,
    info: infoLight,
    danger: dangerLight,
    successBg: Color(0x1F10B981), // 12% emerald
    warningBg: Color(0x2616A34A), // não usado — uso warning real
    infoBg: Color(0x1F3B82F6),
    dangerBg: Color(0x1FEF4444),
    onSemantic: Colors.white,
  );

  // BG correto pra light (warning amber)
  static const BrandTokens lightCorrected = BrandTokens(
    success: successLight,
    warning: warningLight,
    info: infoLight,
    danger: dangerLight,
    successBg: Color(0x1F10B981),
    warningBg: Color(0x26F59E0B), // 15% amber
    infoBg: Color(0x1F3B82F6),
    dangerBg: Color(0x1FEF4444),
    onSemantic: Colors.white,
  );

  static const BrandTokens dark = BrandTokens(
    success: successDark,
    warning: warningDark,
    info: infoDark,
    danger: dangerDark,
    successBg: Color(0x2634D399),
    warningBg: Color(0x33FBBF24),
    infoBg: Color(0x2660A5FA),
    dangerBg: Color(0x26F87171),
    onSemantic: Colors.white,
  );

  @override
  BrandTokens copyWith({
    Color? success,
    Color? warning,
    Color? info,
    Color? danger,
    Color? successBg,
    Color? warningBg,
    Color? infoBg,
    Color? dangerBg,
    Color? onSemantic,
  }) =>
      BrandTokens(
        success: success ?? this.success,
        warning: warning ?? this.warning,
        info: info ?? this.info,
        danger: danger ?? this.danger,
        successBg: successBg ?? this.successBg,
        warningBg: warningBg ?? this.warningBg,
        infoBg: infoBg ?? this.infoBg,
        dangerBg: dangerBg ?? this.dangerBg,
        onSemantic: onSemantic ?? this.onSemantic,
      );

  @override
  BrandTokens lerp(ThemeExtension<BrandTokens>? other, double t) {
    if (other is! BrandTokens) return this;
    return BrandTokens(
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      info: Color.lerp(info, other.info, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      successBg: Color.lerp(successBg, other.successBg, t)!,
      warningBg: Color.lerp(warningBg, other.warningBg, t)!,
      infoBg: Color.lerp(infoBg, other.infoBg, t)!,
      dangerBg: Color.lerp(dangerBg, other.dangerBg, t)!,
      onSemantic: Color.lerp(onSemantic, other.onSemantic, t)!,
    );
  }
}

/// Helper pra acessar tokens via context.
extension BrandContextX on BuildContext {
  BrandTokens get brand => Theme.of(this).extension<BrandTokens>()!;
}
