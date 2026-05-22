import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../branding/brand_tokens.dart';

/// Card de vidro fosco — usado nas telas de auth.
/// Usa BackdropFilter pra blur + fundo translúcido + borda branca sutil.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(BrandTokens.spaceLg),
    this.borderRadius,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final BorderRadius? borderRadius;

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? BorderRadius.circular(BrandTokens.radiusXl);
    return ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.10),
            borderRadius: radius,
            border: Border.all(
              color: Colors.white.withOpacity(0.20),
              width: 1.2,
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}

/// Botão primário com gradient + sombra colorida + haptic-friendly.
class GlassPrimaryButton extends StatelessWidget {
  const GlassPrimaryButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.loading = false,
    this.icon,
  });

  final VoidCallback? onPressed;
  final String label;
  final bool loading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: BrandTokens.gradientPrimary,
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          boxShadow:
              onPressed == null ? null : BrandTokens.shadowColored,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: loading ? null : onPressed,
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
            child: Center(
              child: loading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (icon != null) ...[
                          Icon(icon, color: Colors.white, size: 20),
                          const SizedBox(width: BrandTokens.spaceSm),
                        ],
                        Text(
                          label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                            letterSpacing: 0.2,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Input estilizado pra usar dentro do GlassCard. Fundo branco/10%,
/// borda translúcida, label e texto brancos.
class GlassTextField extends StatelessWidget {
  const GlassTextField({
    super.key,
    required this.controller,
    required this.label,
    this.keyboardType,
    this.inputFormatters = const [],
    this.obscureText = false,
    this.suffixIcon,
    this.prefixIcon,
    this.textStyle,
    this.autofocus = false,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final List<TextInputFormatter> inputFormatters;
  final bool obscureText;
  final Widget? suffixIcon;
  final Widget? prefixIcon;
  final TextStyle? textStyle;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      autofocus: autofocus,
      inputFormatters: inputFormatters,
      style: textStyle ??
          const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: 16,
            letterSpacing: 0.3,
          ),
      cursorColor: Colors.white,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(
          color: Colors.white70,
          fontWeight: FontWeight.w600,
        ),
        floatingLabelStyle: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
        prefixIcon: prefixIcon,
        suffixIcon: suffixIcon,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd,
          vertical: BrandTokens.spaceMd,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.18)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          borderSide: const BorderSide(
            color: BrandTokens.primaryLight,
            width: 2,
          ),
        ),
      ),
    );
  }
}
