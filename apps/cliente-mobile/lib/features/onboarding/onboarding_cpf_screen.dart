import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/contatos_repository.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/sheet_text_field.dart';

class OnboardingCpfScreen extends ConsumerStatefulWidget {
  const OnboardingCpfScreen({super.key});

  @override
  ConsumerState<OnboardingCpfScreen> createState() =>
      _OnboardingCpfScreenState();
}

class _OnboardingCpfScreenState extends ConsumerState<OnboardingCpfScreen> {
  final _ctrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    final cpf = _ctrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF válido com 11 digitos');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).registerStart(cpf);
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case RegisterStartOk(:final maskedPhone):
        context.push('/onboarding/otp', extra: {
          'cpf': cpf,
          'masked_phone': maskedPhone,
        });
      case RegisterStartNotFound():
        await _showNotFoundSheet();
      case RegisterStartError(:final message):
        final lower = message.toLowerCase();
        if (lower.contains('cadastrad')) {
          _toast('Esse CPF já tem conta. Vou te levar pro login.');
          await Future.delayed(const Duration(milliseconds: 700));
          if (!mounted) return;
          // Leva o CPF junto pro login já vir preenchido.
          context.go('/login', extra: {'cpf': cpf});
        } else {
          _toast(message);
        }
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  Future<void> _showNotFoundSheet() async {
    // Busca o contato de WhatsApp com melhor esforço, antes de exibir a
    // sheet, pra decidir se mostra o CTA (sem contato/erro -> some, graceful).
    String? whatsNumber;
    try {
      final contatos =
          await ref.read(contatosOperadoraProvider.future);
      for (final c in contatos) {
        if (c.tipo == 'whatsapp') {
          final digits = c.valor.replaceAll(RegExp(r'\D'), '');
          if (digits.isNotEmpty) whatsNumber = digits;
          break;
        }
      }
    } on Object {
      whatsNumber = null;
    }
    if (!mounted) return;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.search_off_rounded,
                  color: BrandTokens.warning, size: 48),
              const SizedBox(height: BrandTokens.spaceMd),
              Text(
                'Não achamos esse CPF',
                textAlign: TextAlign.center,
                style: Theme.of(sheetContext).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Confere se digitou certinho. Ainda não é cliente Ondeline? '
                'Bora resolver isso agora 😉',
                textAlign: TextAlign.center,
                style: Theme.of(sheetContext).textTheme.bodyMedium,
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              if (whatsNumber != null) ...[
                FilledButton.icon(
                  onPressed: () async {
                    final uri = Uri.parse(
                      'https://wa.me/$whatsNumber'
                      '?text=${Uri.encodeComponent(
                        'Olá! Baixei o app da Ondeline e quero ser cliente 😃',
                      )}',
                    );
                    try {
                      await launchUrl(uri,
                          mode: LaunchMode.externalApplication);
                    } on Object {
                      // Best-effort — se falhar, apenas ignora.
                    }
                  },
                  icon: const Icon(Icons.chat_rounded),
                  label: const Text('Quero ser cliente'),
                  style: FilledButton.styleFrom(
                    backgroundColor: BrandTokens.brandWhatsapp,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(48),
                    shape: RoundedRectangleBorder(
                      borderRadius:
                          BorderRadius.circular(BrandTokens.radiusMd),
                    ),
                    textStyle: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
              ],
              TextButton(
                onPressed: () => Navigator.of(sheetContext).pop(),
                style: TextButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text(
                  'Tentar de novo',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return AuthScaffold(
      icon: Icons.badge_outlined,
      title: 'Vamos te encontrar',
      subtitle: 'Digite o CPF do titular do contrato pra gente localizar seu cadastro.',
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceSm + 2,
              vertical: BrandTokens.spaceXs,
            ),
            decoration: BoxDecoration(
              color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Text(
              'Passo 1 de 3',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: isDark
                    ? BrandTokens.textSecondaryDark
                    : BrandTokens.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceLg),
          Container(
            width: 88,
            height: 88,
            decoration: BoxDecoration(
              gradient: BrandTokens.gradientPrimary,
              shape: BoxShape.circle,
              boxShadow: BrandTokens.shadowColored,
            ),
            child: const Icon(
              Icons.person_search_rounded,
              color: Colors.white,
              size: 44,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceLg),
          SheetTextField(
            controller: _ctrl,
            label: 'CPF',
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(11),
              CpfFormatter(),
            ],
            prefixIcon: Icons.badge_outlined,
          ),
          Container(
            margin: const EdgeInsets.only(top: BrandTokens.spaceLg),
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            decoration: BoxDecoration(
              color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark ? Colors.white12 : BrandTokens.divider,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.verified_user_outlined,
                    color: BrandTokens.primary, size: 22),
                const SizedBox(width: BrandTokens.spaceSm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Por que pedimos seu CPF?',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 2),
                      Text(
                        'Usamos só pra localizar seu contrato na Ondeline. Seus dados ficam protegidos.',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark
                              ? BrandTokens.textSecondaryDark
                              : BrandTokens.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      bottom: Column(
        children: [
          FilledButton(
            onPressed: _loading ? null : _continue,
            style: FilledButton.styleFrom(
              backgroundColor: BrandTokens.primary,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
              ),
              textStyle: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 16,
              ),
            ),
            child: _loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: Colors.white,
                    ),
                  )
                : const Text('Continuar'),
          ),
          TextButton(
            onPressed: () {
              // Se já digitou um CPF válido, leva pro login pré-preenchido.
              final cpf = _ctrl.text.replaceAll(RegExp(r'\D'), '');
              context.go(
                '/login',
                extra: cpf.length == 11 ? {'cpf': cpf} : null,
              );
            },
            style: TextButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
            ),
            child: const Text(
              'Ja tenho conta',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
