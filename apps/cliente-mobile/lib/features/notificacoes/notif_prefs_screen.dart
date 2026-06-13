import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/dto.dart';
import '../../core/api/notificacoes_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/glass_app_bar.dart';

const _categoriaLabels = <String, String>{
  'fatura': 'Faturas',
  'os': 'Chamados (OS)',
  'manutencao': 'Manutenção programada',
  'promocao': 'Promoções',
  'conta': 'Minha conta',
};

const _categoriaDescricoes = <String, String>{
  'fatura': 'Fatura nova, vencimento próximo, pagamento confirmado.',
  'os': 'Atualizações do seu chamado de suporte.',
  'manutencao': 'Avisos de manutenção programada na sua região.',
  'promocao': 'Ofertas e novidades pra clientes.',
  'conta': 'Mudanças na sua conta ou login suspeito.',
};

const _categoriaIcons = <String, IconData>{
  'fatura': Icons.receipt_long_rounded,
  'os': Icons.support_agent_rounded,
  'manutencao': Icons.build_rounded,
  'promocao': Icons.local_offer_rounded,
  'conta': Icons.person_rounded,
};

const _categoriaCor = <String, Color>{
  'fatura': BrandTokens.catBilling,
  'os': BrandTokens.catSupport,
  'manutencao': BrandTokens.warning,
  'promocao': BrandTokens.catPlan,
  'conta': BrandTokens.info,
};

class NotifPrefsScreen extends ConsumerStatefulWidget {
  const NotifPrefsScreen({super.key});

  @override
  ConsumerState<NotifPrefsScreen> createState() => _NotifPrefsScreenState();
}

class _NotifPrefsScreenState extends ConsumerState<NotifPrefsScreen> {
  Map<String, bool>? _local;
  bool _saving = false;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(notifPrefsProvider);
    final topPad = MediaQuery.paddingOf(context).top +
        kToolbarHeight +
        BrandTokens.spaceMd;
    return Scaffold(
      appBar: const GlassAppBar(title: 'Preferências'),
      extendBodyBehindAppBar: true,
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(
          child: Text('Não conseguimos carregar as preferências.'),
        ),
        data: (prefs) {
          final current = _local ?? Map<String, bool>.from(prefs.categorias);
          return ListView(
            padding: EdgeInsets.fromLTRB(
              BrandTokens.spaceLg,
              topPad,
              BrandTokens.spaceLg,
              BrandTokens.spaceLg,
            ),
            children: [
              const Text(
                'Escolha o que você quer receber. Você sempre pode mudar aqui.',
                style: TextStyle(
                  color: BrandTokens.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              for (final cat in _categoriaLabels.keys)
                _PrefTile(
                  categoria: cat,
                  ativo: current[cat] ?? true,
                  onChanged: (v) => setState(() {
                    _local = {...current, cat: v};
                  }),
                ),
              const SizedBox(height: BrandTokens.spaceLg),
              SizedBox(
                height: 52,
                child: FilledButton(
                  onPressed: _saving || _local == null
                      ? null
                      : () => _save(NotifPrefsDto(categorias: _local!)),
                  child: _saving
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text(
                          'Salvar',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _save(NotifPrefsDto prefs) async {
    setState(() => _saving = true);
    try {
      await ref.read(notificacoesRepositoryProvider).setPrefs(prefs);
      if (!mounted) return;
      ref.invalidate(notifPrefsProvider);
      setState(() {
        _local = null;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Preferências salvas.')),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao salvar.')),
      );
    }
  }
}

class _PrefTile extends StatelessWidget {
  const _PrefTile({
    required this.categoria,
    required this.ativo,
    required this.onChanged,
  });
  final String categoria;
  final bool ativo;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cor = _categoriaCor[categoria] ?? BrandTokens.primary;
    final ico = _categoriaIcons[categoria] ?? Icons.notifications_rounded;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      child: Container(
        padding: const EdgeInsets.all(BrandTokens.spaceMd),
        decoration: BoxDecoration(
          color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          border: Border.all(
            color: isDark ? Colors.white12 : BrandTokens.divider,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: cor.withOpacity(0.14),
                borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
              ),
              child: Icon(ico, color: cor, size: 20),
            ),
            const SizedBox(width: BrandTokens.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _categoriaLabels[categoria] ?? categoria,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                  Text(
                    _categoriaDescricoes[categoria] ?? '',
                    style: const TextStyle(
                      fontSize: 12,
                      color: BrandTokens.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            Switch(value: ativo, onChanged: onChanged),
          ],
        ),
      ),
    );
  }
}
