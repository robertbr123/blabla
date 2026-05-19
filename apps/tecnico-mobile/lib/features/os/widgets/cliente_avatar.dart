import 'package:flutter/material.dart';

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

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [color, _escurecer(color, 0.12)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
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

  static const _palette = <Color>[
    Color(0xFF2563eb), // blue
    Color(0xFF06b6d4), // cyan
    Color(0xFF16a34a), // green
    Color(0xFFf59e0b), // amber
    Color(0xFFef4444), // red
    Color(0xFF8b5cf6), // violet
    Color(0xFFec4899), // pink
    Color(0xFF14b8a6), // teal
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
