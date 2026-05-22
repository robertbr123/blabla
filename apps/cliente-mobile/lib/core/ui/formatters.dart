import 'package:flutter/services.dart';

/// Helpers de formatação BR (CPF, telefone).
///
/// Uso em TextField:
///   TextField(inputFormatters: [CpfFormatter()])
///
/// Uso em display:
///   Text(formatCpf('12345678901'))         → '123.456.789-01'
///   Text(formatTelefone('47999998888'))    → '(47) 99999-8888'
///   Text(formatCpfMask4('12345678901'))    → '***.***.***-01'
String _onlyDigits(String s) => s.replaceAll(RegExp(r'\D'), '');

/// Formata CPF: 12345678901 → 123.456.789-01
/// Aceita string parcial (ex: '12345' → '123.45').
String formatCpf(String raw) {
  final d = _onlyDigits(raw);
  if (d.isEmpty) return '';
  final buf = StringBuffer();
  for (var i = 0; i < d.length && i < 11; i++) {
    if (i == 3 || i == 6) buf.write('.');
    if (i == 9) buf.write('-');
    buf.write(d[i]);
  }
  return buf.toString();
}

/// Mascara só dos 4 últimos: 12345678901 → ***.***.***-01
String formatCpfMask4(String last4OrFull) {
  final d = _onlyDigits(last4OrFull);
  if (d.isEmpty) return '***.***.***-**';
  final last4 = d.length >= 4 ? d.substring(d.length - 4) : d.padLeft(4, '*');
  return '***.***.***-${last4.padLeft(2, '*').substring(last4.length - 2)}';
}

/// Formata telefone BR — celular (11 dig) ou fixo (10 dig).
/// 47999998888 → (47) 99999-8888
/// 4732234567  → (47) 3223-4567
String formatTelefone(String raw) {
  final d = _onlyDigits(raw);
  if (d.isEmpty) return '';
  if (d.length <= 2) return '($d';
  if (d.length <= 6) return '(${d.substring(0, 2)}) ${d.substring(2)}';
  if (d.length <= 10) {
    // Fixo 10 dígitos: (47) 3223-4567 — corte em 6
    final ddd = d.substring(0, 2);
    final p1 = d.substring(2, d.length < 6 ? d.length : 6);
    final p2 = d.length > 6 ? d.substring(6) : '';
    return p2.isEmpty ? '($ddd) $p1' : '($ddd) $p1-$p2';
  }
  // Celular 11 dígitos: (47) 99999-8888
  final ddd = d.substring(0, 2);
  final p1 = d.substring(2, 7);
  final p2 = d.substring(7, d.length > 11 ? 11 : d.length);
  return '($ddd) $p1-$p2';
}

// ════════ TextInputFormatters ════════

/// Formata CPF enquanto o usuário digita.
class CpfFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = _onlyDigits(newValue.text);
    if (digits.length > 11) {
      return oldValue;
    }
    final formatted = formatCpf(digits);
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}

/// Formata telefone enquanto o usuário digita.
class TelefoneFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = _onlyDigits(newValue.text);
    if (digits.length > 11) {
      return oldValue;
    }
    final formatted = formatTelefone(digits);
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}
