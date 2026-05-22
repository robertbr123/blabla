import 'package:flutter/material.dart';

/// Mapeamento de nomes de icone (string vinda do admin) pra IconData.
/// Lista limitada porque o Flutter tree-shakes Icons em builds AOT —
/// só icones referenciados estaticamente sobrevivem. Admin precisa
/// usar um destes nomes; outros caem no fallback (campaign).
const _promoIcons = <String, IconData>{
  'rocket_launch_rounded': Icons.rocket_launch_rounded,
  'card_giftcard_rounded': Icons.card_giftcard_rounded,
  'shield_rounded': Icons.shield_rounded,
  'wifi_rounded': Icons.wifi_rounded,
  'percent_rounded': Icons.percent_rounded,
  'star_rounded': Icons.star_rounded,
  'local_offer_rounded': Icons.local_offer_rounded,
  'celebration_rounded': Icons.celebration_rounded,
  'flash_on_rounded': Icons.flash_on_rounded,
  'autorenew_rounded': Icons.autorenew_rounded,
  'home_repair_service_rounded': Icons.home_repair_service_rounded,
  'support_agent_rounded': Icons.support_agent_rounded,
  'payments_rounded': Icons.payments_rounded,
  'group_rounded': Icons.group_rounded,
  'campaign_rounded': Icons.campaign_rounded,
};

IconData promoIconOf(String? name) {
  if (name == null) return Icons.campaign_rounded;
  return _promoIcons[name] ?? Icons.campaign_rounded;
}

/// Lista de nomes suportados — pode ser usado pra ajudar admin/dashboard.
List<String> supportedPromoIcons() => _promoIcons.keys.toList();
