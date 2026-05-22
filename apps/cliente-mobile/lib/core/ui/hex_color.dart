import 'package:flutter/painting.dart';

/// Parser de cor hex no formato "#RRGGBB" ou "#RRGGBBAA". Retorna null
/// se inválida — caller usa default.
Color? hexColor(String? s) {
  if (s == null) return null;
  var h = s.trim();
  if (h.startsWith('#')) h = h.substring(1);
  if (h.length == 6) h = 'FF$h';
  if (h.length == 8) {
    final n = int.tryParse(h, radix: 16);
    if (n != null) return Color(n);
  }
  return null;
}
