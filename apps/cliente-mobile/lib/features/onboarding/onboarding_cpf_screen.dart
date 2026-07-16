import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/contatos_repository.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/sheet_text_field.dart';
import '../../core/ui/whatsapp_comercial.dart';

const _kMensagemQueroSerCliente =
    'Olá! Baixei o app da Ondeline e quero ser cliente 😃';

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
      case RegisterStartAlreadyExists():
        await _showAlreadyExistsSheet(cpf);
      case RegisterStartSemTelefone():
        await _showSemTelefoneSheet(cpf);
      case RegisterStartError(:final message):
        _toast(message);
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  Future<void> _showNotFoundSheet() async {
    // Busca o contato de WhatsApp com melhor esforço, antes de exibir a
    // sheet, pra decidir se mostra o CTA (sem contato/erro -> some, graceful).
    String? whatsNumber;
    try {
      final contatos = await ref.read(contatosOperadoraProvider.future);
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
    FocusManager.instance.primaryFocus?.unfocus();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      builder: (sheetContext) => SingleChildScrollView(
        child: SafeArea(
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
                    onPressed: () => abrirWhatsappComercial(
                      ref,
                      mensagem: _kMensagemQueroSerCliente,
                    ),
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
      ),
    );
  }

  Future<void> _showAlreadyExistsSheet(String cpf) async {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    FocusManager.instance.primaryFocus?.unfocus();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      builder: (sheetContext) => SingleChildScrollView(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
            MediaQuery.viewInsetsOf(sheetContext).bottom + BrandTokens.spaceLg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.celebration_rounded,
                  color: BrandTokens.primary, size: 48),
              const SizedBox(height: BrandTokens.spaceMd),
              Text(
                'Você já tem conta!',
                textAlign: TextAlign.center,
                style: Theme.of(sheetContext).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Esse CPF já está cadastrado. Bora entrar? Se esqueceu a '
                'senha, dá pra recuperar na tela de login.',
                textAlign: TextAlign.center,
                style: Theme.of(sheetContext).textTheme.bodyMedium,
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              FilledButton(
                onPressed: () => Navigator.of(sheetContext).pop(),
                style: FilledButton.styleFrom(
                  backgroundColor: BrandTokens.primary,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(48),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                  ),
                  textStyle: const TextStyle(fontWeight: FontWeight.w800),
                ),
                child: const Text('Ir pro login'),
              ),
            ],
          ),
        ),
      ),
    );
    if (!mounted) return;
    // Leva o CPF junto pro login já vir preenchido.
    context.go('/login', extra: {'cpf': cpf});
  }

  Future<void> _showSemTelefoneSheet(String cpf) async {
    FocusManager.instance.primaryFocus?.unfocus();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusFolha),
        ),
      ),
      builder: (sheetContext) => SingleChildScrollView(
        child: SafeArea(
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
                const Icon(Icons.phone_disabled_rounded,
                    color: BrandTokens.warning, size: 48),
                const SizedBox(height: BrandTokens.spaceMd),
                Text(
                  'Achamos seu cadastro, mas...',
                  textAlign: TextAlign.center,
                  style: Theme.of(sheetContext).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                      ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
                Text(
                  'Ele está sem um WhatsApp válido. Fala com a gente que '
                  'atualizamos rapidinho — aí é só voltar e continuar.',
                  textAlign: TextAlign.center,
                  style: Theme.of(sheetContext).textTheme.bodyMedium,
                ),
                const SizedBox(height: BrandTokens.spaceLg),
                FilledButton.icon(
                  onPressed: () => abrirWhatsappComercial(
                    ref,
                    mensagem: 'Olá! Quero atualizar o telefone do meu '
                        'cadastro pra acessar o app. Meu CPF é '
                        '${formatCpf(cpf)}.',
                  ),
                  icon: const Icon(Icons.chat_rounded),
                  label: const Text('Atualizar meu cadastro'),
                  style: FilledButton.styleFrom(
                    backgroundColor: BrandTokens.brandWhatsapp,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(48),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                    ),
                    textStyle: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                const SizedBox(height: BrandTokens.spaceSm),
                TextButton(
                  onPressed: () => Navigator.of(sheetContext).pop(),
                  style: TextButton.styleFrom(
                    minimumSize: const Size.fromHeight(48),
                  ),
                  child: const Text(
                    'Fechar',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
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
      subtitle:
          'Digite o CPF do titular do contrato pra gente localizar seu cadastro.',
      child: Column(
        children: [
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
                          style: TextStyle(
                              fontSize: 13, fontWeight: FontWeight.w800)),
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
          const SizedBox(height: BrandTokens.spaceSm),
          Text(
            'Ainda não é cliente?',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: isDark
                  ? BrandTokens.textSecondaryDark
                  : BrandTokens.textSecondary,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceSm),
          OutlinedButton.icon(
            onPressed: () async {
              final ok = await abrirWhatsappComercial(
                ref,
                mensagem: _kMensagemQueroSerCliente,
              );
              if (!ok && mounted) {
                _toast(
                  'Não conseguimos abrir o WhatsApp agora. '
                  'Tenta de novo mais tarde.',
                );
              }
            },
            icon: const Icon(Icons.chat_rounded),
            label: const Text('Quero ser cliente'),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(
                color: BrandTokens.brandWhatsapp,
                width: 1.2,
              ),
              foregroundColor: BrandTokens.brandWhatsapp,
              minimumSize: const Size.fromHeight(48),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
              ),
              textStyle: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }
}
