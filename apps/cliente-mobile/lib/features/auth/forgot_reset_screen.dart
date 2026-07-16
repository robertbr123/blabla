import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/capa_folha.dart';
import '../../core/ui/haptics.dart';
import '../../core/ui/sheet_text_field.dart';

/// Reset de senha em uma tela: código (OTP reset_pwd) + nova senha.
/// Em sucesso o backend devolve token e o usuário já entra logado.
class ForgotResetScreen extends ConsumerStatefulWidget {
  const ForgotResetScreen({super.key, required this.cpf, this.maskedPhone = ''});
  final String cpf;
  final String maskedPhone;

  @override
  ConsumerState<ForgotResetScreen> createState() => _ForgotResetScreenState();
}

class _ForgotResetScreenState extends ConsumerState<ForgotResetScreen> {
  final _code = TextEditingController();
  final _p1 = TextEditingController();
  final _p2 = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _code.dispose();
    _p1.dispose();
    _p2.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_code.text.trim().length != 6) {
      _toast('Digite o código de 6 dígitos');
      return;
    }
    if (_p1.text.length < 8) {
      _toast('Senha deve ter ao menos 8 caracteres');
      return;
    }
    if (_p1.text != _p2.text) {
      _toast('Senhas não conferem');
      return;
    }
    setState(() => _loading = true);
    final r = await ref.read(authRepositoryProvider).forgotReset(
          cpf: widget.cpf,
          code: _code.text.trim(),
          password: _p1.text,
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Capa compacta com botão voltar + título ──
            CapaBackground(
              padding: EdgeInsets.only(
                left: BrandTokens.spaceLg,
                right: BrandTokens.spaceLg,
                top: MediaQuery.paddingOf(context).top + BrandTokens.spaceLg,
                bottom: BrandTokens.spaceXl,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IconButton(
                    onPressed: () => context.pop(),
                    icon: const Icon(
                      Icons.arrow_back_rounded,
                      color: BrandTokens.capaInk,
                    ),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                  const SizedBox(height: BrandTokens.spaceMd),
                  const Text(
                    'Redefinir senha',
                    style: TextStyle(
                      color: BrandTokens.capaInk,
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.6,
                    ),
                  ),
                  const SizedBox(height: BrandTokens.spaceXs),
                  Text(
                    'Digite o código que enviamos no seu WhatsApp.',
                    style: TextStyle(
                      color: BrandTokens.capaInk.withValues(alpha: 0.7),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            // ── Folha com o formulário ──
            Expanded(
              child: SingleChildScrollView(
                child: FolhaContainer(
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
                        controller: _code,
                        label: 'Código (6 dígitos)',
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(6),
                        ],
                        prefixIcon: Icons.sms_outlined,
                      ),
                      const SizedBox(height: BrandTokens.spaceMd),
                      SheetTextField(
                        controller: _p1,
                        label: 'Nova senha',
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
                      const SizedBox(height: BrandTokens.spaceMd),
                      SheetTextField(
                        controller: _p2,
                        label: 'Confirme a nova senha',
                        obscureText: _hide,
                        prefixIcon: Icons.lock_outline,
                      ),
                      const SizedBox(height: BrandTokens.spaceMd),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
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
                            : const Text('Redefinir senha'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
