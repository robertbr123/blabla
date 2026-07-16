import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../branding/brand_tokens.dart';

/// Campo de texto da folha clara — surface branca/marinho, borda que acende
/// em ciano no foco. Substitui o GlassTextField nas telas de auth novas.
class SheetTextField extends StatelessWidget {
  const SheetTextField({
    super.key,
    required this.controller,
    required this.label,
    this.keyboardType,
    this.inputFormatters,
    this.obscureText = false,
    this.prefixIcon,
    this.suffix,
    this.autofocus = false,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final IconData? prefixIcon;
  final Widget? suffix;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      obscureText: obscureText,
      autofocus: autofocus,
      style: TextStyle(
        fontWeight: FontWeight.w600,
        color: isDark ? BrandTokens.textPrimaryDark : BrandTokens.textPrimary,
      ),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: prefixIcon == null ? null : Icon(prefixIcon, size: 20),
        suffixIcon: suffix,
        filled: true,
        fillColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : BrandTokens.divider,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(
            color: isDark ? Colors.white12 : BrandTokens.divider,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: const BorderSide(color: BrandTokens.primary, width: 1.5),
        ),
      ),
    );
  }
}
