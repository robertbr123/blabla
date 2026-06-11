import 'package:flutter/material.dart';

/// Design tokens do app do cliente final. Paleta da logo Ondeline:
/// ciano + azul marinho profundo.
class BrandTokens {
  BrandTokens._();

  // Cores principais — derivadas da logo
  static const Color primary = Color(0xFF14B8B0); // Ciano Ondeline
  static const Color primaryDark = Color(0xFF0B1F3A); // Azul marinho fundo da logo
  static const Color primaryLight = Color(0xFF5FE3DC);
  static const Color accent = Color(0xFF14B8B0);
  static const Color accentDark = Color(0xFF0F8F89);

  // Neutros (light)
  static const Color background = Color(0xFFF4F8FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF0B1F3A);
  static const Color textSecondary = Color(0xFF5B6F8A);
  static const Color divider = Color(0xFFE3EBF0);

  // Neutros (dark) — usa o azul marinho da logo como fundo
  static const Color backgroundDark = Color(0xFF051329);
  static const Color surfaceDark = Color(0xFF0B1F3A);
  static const Color textPrimaryDark = Color(0xFFEFF7F8);
  static const Color textSecondaryDark = Color(0xFF8FA3BD);

  // Status
  static const Color success = Color(0xFF14B8B0); // ciano da marca — ver successBright pra gradientes de "ativo"
  static const Color warning = Color(0xFFE8A33D);
  static const Color danger = Color(0xFFE0455A);
  static const Color info = Color(0xFF3B82F6);

  // Cores categóricas pra quick actions (ícones com personalidade)
  static const Color catBilling = Color(0xFF14B8B0); // ciano
  static const Color catSupport = Color(0xFF8B5CF6); // roxo
  static const Color catConnection = Color(0xFFE0455A); // vermelho/coral
  static const Color catPlan = Color(0xFFE8A33D); // âmbar

  // Tons derivados de status (usados em gradientes/ênfase)
  static const Color successBright = Color(0xFF22E0A1); // verde conexão ok
  static const Color dangerDeep = Color(0xFFB12B40); // fim de gradiente vencida
  static const Color dangerStrong = Color(0xFFCC2233); // barra breaking de manutenção
  static const Color warningBright = Color(0xFFF59E0B); // fim de gradiente de status suspenso
  static const Color neutralGrey = Color(0xFF6B7280); // status desconhecido
  static const Color neutralGreyDark = Color(0xFF374151); // fundo do gradiente de status desconhecido

  // Cores de marca de terceiros (canais de contato)
  static const Color brandWhatsapp = Color(0xFF25D366);
  static const Color brandWhatsappDark = Color(0xFF128C7E);
  static const Color brandInstagram = Color(0xFFE1306C);
  static const Color brandFacebook = Color(0xFF1877F2);

  // Tons de destaque pontuais
  static const Color accentOrange = Color(0xFFFF8E53); // gradiente quick card
  static const Color accentPink = Color(0xFFFF6B9D); // banner aniversariante

  // Fallback de gradiente de promoção (quando admin não define cores)
  static const Color promoFallbackFrom = Color(0xFF8B5CF6); // mesmo tom de catSupport — coincidência de paleta, não dependência
  static const Color promoFallbackTo = Color(0xFF5B6CFF);

  // Raios
  static const double radiusSm = 12;
  static const double radiusMd = 16;
  static const double radiusLg = 24;
  static const double radiusXl = 32;
  static const double radius2xl = 40;

  // Espacos
  static const double spaceXs = 4;
  static const double spaceSm = 8;
  static const double spaceMd = 16;
  static const double spaceLg = 24;
  static const double spaceXl = 32;
  static const double spaceXxl = 48;

  // Motion (durações padrão)
  static const Duration motionFast = Duration(milliseconds: 150);
  static const Duration motionMedium = Duration(milliseconds: 300);
  static const Duration motionSlow = Duration(milliseconds: 600);
  static const Duration motionAmbient = Duration(seconds: 12);

  // Gradients reutilizáveis
  static const LinearGradient gradientHero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, primaryDark],
  );

  static const LinearGradient gradientPrimary = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [primary, primaryLight],
  );

  static const LinearGradient gradientAuthBg = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primaryDark, Color(0xFF0A2A4E), Color(0xFF0F5A6E), primary],
    stops: [0.0, 0.4, 0.75, 1.0],
  );

  // Sombras
  static final List<BoxShadow> shadowSoft = [
    BoxShadow(
      color: primaryDark.withOpacity(0.10),
      blurRadius: 24,
      offset: const Offset(0, 8),
    ),
  ];

  static final List<BoxShadow> shadowCard = [
    BoxShadow(
      color: primaryDark.withOpacity(0.05),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];

  // Elevations
  static final List<BoxShadow> elevation1 = [
    BoxShadow(
      color: primaryDark.withOpacity(0.04),
      blurRadius: 8,
      offset: const Offset(0, 2),
    ),
  ];

  static final List<BoxShadow> elevation2 = [
    BoxShadow(
      color: primaryDark.withOpacity(0.08),
      blurRadius: 16,
      offset: const Offset(0, 6),
    ),
  ];

  static final List<BoxShadow> elevation3 = [
    BoxShadow(
      color: primaryDark.withOpacity(0.12),
      blurRadius: 28,
      offset: const Offset(0, 12),
    ),
  ];

  // Sombra colorida (usada em botões/CTAs principais)
  static final List<BoxShadow> shadowColored = [
    BoxShadow(
      color: primary.withOpacity(0.35),
      blurRadius: 20,
      offset: const Offset(0, 8),
    ),
  ];
}
