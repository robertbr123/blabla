import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/pressable_scale.dart';

/// Card de destaque da Minha Rede na home: dispositivos conectados + selo de
/// sinal ao vivo + atalho de trocar senha. Some pra quem nao tem ONU mapeada
/// (encontrada=false) ou quando a consulta falha — nesses casos o icone em
/// "Acoes rapidas" continua como acesso. Toca -> /rede.
class RedeDestaqueCard extends ConsumerWidget {
  const RedeDestaqueCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(redeAparelhosProvider);
    return async.when(
      loading: () => const _Skeleton(),
      // Erro (rede/GenieACS): nao da pra saber se a ONU existe -> esconde.
      error: (_, __) => const SizedBox.shrink(),
      data: (d) =>
          d.encontrada ? _Card(dados: d) : const SizedBox.shrink(),
    );
  }
}

/// Cores/icone/label do selo de sinal — espelha o _SaudeBadge da rede_screen,
/// em versao compacta (so o essencial pro chip).
({Color cor, IconData icon, String label}) _selo(String saude) {
  switch (saude) {
    case 'excelente':
      return (
        cor: BrandTokens.success,
        icon: Icons.signal_cellular_alt_rounded,
        label: 'Ótimo',
      );
    case 'boa':
      return (
        cor: BrandTokens.primary,
        icon: Icons.signal_cellular_alt_rounded,
        label: 'Bom',
      );
    case 'fraca':
      return (
        cor: BrandTokens.warning,
        icon: Icons.signal_cellular_alt_2_bar_rounded,
        label: 'Fraco',
      );
    default:
      return (
        cor: BrandTokens.info,
        icon: Icons.wifi_tethering_rounded,
        label: 'Ativo',
      );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.dados});
  final RedeAparelhosDto dados;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? BrandTokens.surfaceDark : BrandTokens.surface;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;
    final selo = _selo(dados.saude);
    final n = dados.total;
    final aparelhosLabel =
        '$n ${n == 1 ? 'aparelho conectado' : 'aparelhos conectados'}';

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: PressableScale(
        onTap: () => context.push('/rede'),
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: BrandTokens.shadowCard,
            border: Border.all(
              color: isDark ? Colors.white10 : BrandTokens.divider,
            ),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: BrandTokens.gradientPrimary,
                      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                    ),
                    child: const Icon(
                      Icons.wifi_rounded,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: BrandTokens.spaceMd),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Minha Rede',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          aparelhosLabel,
                          style: TextStyle(fontSize: 13, color: secondary),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: selo.cor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(selo.icon, color: selo.cor, size: 14),
                        const SizedBox(width: 4),
                        Text(
                          selo.label,
                          style: TextStyle(
                            color: selo.cor,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Divider(
                height: 1,
                color: isDark ? Colors.white10 : BrandTokens.divider,
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Row(
                children: [
                  Icon(
                    Icons.key_rounded,
                    size: 18,
                    color: isDark ? BrandTokens.primaryLight : BrandTokens.primary,
                  ),
                  const SizedBox(width: BrandTokens.spaceSm),
                  const Expanded(
                    child: Text(
                      'Trocar senha do WiFi',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  Icon(Icons.arrow_forward_rounded, size: 16, color: secondary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Skeleton extends StatelessWidget {
  const _Skeleton();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: Container(
        height: 104,
        decoration: BoxDecoration(
          color: isDark ? Colors.white10 : BrandTokens.divider,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        ),
      ),
    );
  }
}
