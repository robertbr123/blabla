import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/capa_folha.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/haptics.dart';
import '../../core/ui/sheet_text_field.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.initialCpf});

  /// CPF pra pré-preencher (ex: veio do onboarding quando o CPF já tinha
  /// conta). Evita o cliente redigitar o que acabou de informar.
  final String? initialCpf;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _cpfCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void initState() {
    super.initState();
    final cpf = widget.initialCpf;
    if (cpf != null && cpf.length == 11) {
      _cpfCtrl.text = formatCpf(cpf);
      return;
    }
    // Sem CPF vindo do onboarding: tenta o último CPF logado (best-effort;
    // storage pode falhar em testes/simulador sem keychain — ignora).
    readLastCpf().then((saved) {
      if (!mounted || saved == null || saved.length != 11) return;
      if (_cpfCtrl.text.isNotEmpty) return;
      setState(() => _cpfCtrl.text = formatCpf(saved));
    }).catchError((_) {});
  }

  @override
  void dispose() {
    _cpfCtrl.dispose();
    _pwdCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe um CPF válido');
      return;
    }
    if (_pwdCtrl.text.length < 8) {
      _toast('Senha curta');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).login(
          cpf: cpf,
          password: _pwdCtrl.text,
        );
    if (!mounted) return;
    setState(() => _loading = false);
    switch (r) {
      case AuthOk():
        await Haptics.success();
        ref.read(authRefreshProvider).bump();
        context.go('/home');
      case AuthError(:final message):
        await Haptics.error();
        _toast(message);
    }
  }

  Future<void> _forgot() async {
    final cpf = _cpfCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (cpf.length != 11) {
      _toast('Informe seu CPF primeiro');
      return;
    }
    setState(() => _loading = true);
    await ref.read(authRepositoryProvider).forgot(cpf);
    if (!mounted) return;
    setState(() => _loading = false);
    _toast(
        'Se o CPF estiver cadastrado, você recebera um código no WhatsApp.');
    // Vai pra tela de reset (digita codigo + nova senha). Navega sempre, mesmo
    // se o CPF nao existir — preserva o "nao revelar se CPF existe"; o reset
    // simplesmente falha no codigo se nenhum OTP foi enviado.
    context.push('/forgot/reset', extra: {'cpf': cpf});
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
      resizeToAvoidBottomInset: true,
      body: GestureDetector(
        onTap: () => FocusScope.of(context).unfocus(),
        behavior: HitTestBehavior.translucent,
        child: CustomScrollView(
          slivers: [
            SliverFillRemaining(
              hasScrollBody: false,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── Capa ciano com tipografia display ──
                  Expanded(
                    child: CapaBackground(
                      padding: EdgeInsets.only(
                        left: BrandTokens.spaceLg,
                        right: BrandTokens.spaceLg,
                        top: MediaQuery.paddingOf(context).top + BrandTokens.spaceXl,
                        bottom: BrandTokens.spaceXl + BrandTokens.radiusFolha,
                      ),
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text('onde\nvocê\nestiver.', style: BrandTokens.displayTitle),
                          SizedBox(height: BrandTokens.spaceSm),
                          Text(
                            'Ondeline — internet que acompanha você.',
                            style: TextStyle(
                              color: BrandTokens.capaInk,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // ── Folha com o formulário ──
                  FolhaContainer(
                    overlap: BrandTokens.radiusFolha,
                    padding: EdgeInsets.fromLTRB(
                      BrandTokens.spaceLg,
                      BrandTokens.spaceLg,
                      BrandTokens.spaceLg,
                      MediaQuery.paddingOf(context).bottom + BrandTokens.spaceLg,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SheetTextField(
                          controller: _cpfCtrl,
                          label: 'CPF',
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            LengthLimitingTextInputFormatter(11),
                            CpfFormatter(),
                          ],
                          prefixIcon: Icons.badge_outlined,
                        ),
                        const SizedBox(height: BrandTokens.spaceMd),
                        SheetTextField(
                          controller: _pwdCtrl,
                          label: 'Senha',
                          obscureText: _hide,
                          prefixIcon: Icons.lock_outline,
                          suffix: IconButton(
                            icon: Icon(
                              _hide
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              size: 20,
                            ),
                            onPressed: () => setState(() => _hide = !_hide),
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceSm),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: _loading ? null : _forgot,
                            style: TextButton.styleFrom(
                              foregroundColor: BrandTokens.primary,
                              padding: EdgeInsets.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text(
                              'Esqueci minha senha',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),
                        const SizedBox(height: BrandTokens.spaceMd),
                        FilledButton(
                          onPressed: _loading ? null : _login,
                          style: FilledButton.styleFrom(
                            backgroundColor: BrandTokens.primary,
                            foregroundColor: Colors.white,
                            minimumSize: const Size.fromHeight(52),
                            shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(BrandTokens.radiusMd),
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
                              : const Text('Entrar'),
                        ),
                        const SizedBox(height: BrandTokens.spaceSm),
                        TextButton(
                          onPressed: _loading
                              ? null
                              : () => context.go('/onboarding/cpf'),
                          style: TextButton.styleFrom(
                            minimumSize: const Size.fromHeight(44),
                            foregroundColor: isDark
                                ? BrandTokens.textPrimaryDark
                                : BrandTokens.textPrimary,
                          ),
                          child: const Text.rich(
                            TextSpan(
                              text: 'Novo aqui? ',
                              children: [
                                TextSpan(
                                  text: 'Criar conta',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    color: BrandTokens.primary,
                                  ),
                                ),
                              ],
                            ),
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
      ),
    );
  }
}
