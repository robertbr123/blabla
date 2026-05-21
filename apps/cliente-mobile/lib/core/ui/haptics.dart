import 'package:flutter/services.dart';

/// Wrappers de haptic feedback. Centraliza pra ficar facil ajustar tom global.
class Haptics {
  Haptics._();

  /// Feedback leve — taps em itens de lista, abrir bottom sheets.
  static Future<void> light() => HapticFeedback.lightImpact();

  /// Feedback medio — acoes confirmatorias (copiar, abrir).
  static Future<void> medium() => HapticFeedback.mediumImpact();

  /// Feedback de sucesso — login OK, OS aberta.
  static Future<void> success() => HapticFeedback.mediumImpact();

  /// Feedback de erro — falha em acao.
  static Future<void> error() => HapticFeedback.heavyImpact();
}
