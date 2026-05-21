import 'package:flutter/material.dart';

import '../../../core/branding/brand_tokens.dart';

/// Avatar circular com inicial(is) do cliente. Cor estavel derivada do nome
/// (mesmo cliente sempre tem mesma cor).
class ClienteAvatar extends StatelessWidget {
  final String? nome;
  final double size;

  const ClienteAvatar({super.key, this.nome, this.size = 44});

  @override
  Widget build(BuildContext context) {
    final iniciais = _iniciais(nome);
    final color = _corDoNome(nome);
    final scheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.18),
            blurRadius: size * 0.36,
            offset: Offset(0, size * 0.12),
          ),
        ],
      ),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            colors: [color, _escurecer(color, 0.12)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(
            color: scheme.surface.withValues(alpha: 0.88),
            width: size * 0.05,
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          iniciais,
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: size * 0.40,
            letterSpacing: 0.2,
          ),
        ),
      ),
    );
  }

  static String _iniciais(String? nome) {
    if (nome == null || nome.trim().isEmpty) return '—';
    final partes = nome.trim().split(RegExp(r'\s+'));
    if (partes.length == 1) {
      return partes[0].substring(0, partes[0].length.clamp(0, 2)).toUpperCase();
    }
    final first = partes.first.isNotEmpty ? partes.first[0] : '';
    final last = partes.last.isNotEmpty ? partes.last[0] : '';
    return (first + last).toUpperCase();
  }

  // Paleta estável pra hashing — emerald + slate + cores neutras saturadas.
  static const _palette = <Color>[
    BrandTokens.emerald500,
    BrandTokens.emerald600,
    Color(0xFF3B82F6), // blue-500
    Color(0xFFF59E0B), // amber-500
    Color(0xFFEF4444), // red-500
    Color(0xFF7E6AAB),
    Color(0xFFB15E78),
    Color(0xFF3B8F84),
  ];

  static Color _corDoNome(String? nome) {
    if (nome == null || nome.isEmpty) return _palette[0];
    int h = 0;
    for (final c in nome.codeUnits) {
      h = (h * 31 + c) & 0x7fffffff;
    }
    return _palette[h % _palette.length];
  }

  static Color _escurecer(Color c, double amount) {
    final hsl = HSLColor.fromColor(c);
    final l = (hsl.lightness - amount).clamp(0.0, 1.0);
    return hsl.withLightness(l).toColor();
  }
}
