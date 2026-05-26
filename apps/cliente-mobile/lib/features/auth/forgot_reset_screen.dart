import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/auth_scaffold.dart';
import '../../core/ui/glass_card.dart';
import '../../core/ui/haptics.dart';

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
    final sub = widget.maskedPhone.isNotEmpty
        ? 'Enviamos um código pro WhatsApp ${widget.maskedPhone}. '
            'Digite-o e escolha uma nova senha.'
        : 'Digite o código que enviamos no seu WhatsApp e escolha uma nova senha.';
    return AuthScaffold(
      showBack: true,
      icon: Icons.lock_reset_rounded,
      title: 'Redefinir senha',
      subtitle: sub,
      child: GlassCard(
        child: Column(
          children: [
            GlassTextField(
              controller: _code,
              label: 'Código (6 dígitos)',
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(6),
              ],
              prefixIcon: const Icon(Icons.sms_outlined,
                  color: Colors.white70, size: 20),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            GlassTextField(
              controller: _p1,
              label: 'Nova senha',
              obscureText: _hide,
              prefixIcon: const Icon(Icons.lock_outline,
                  color: Colors.white70, size: 20),
              suffixIcon: IconButton(
                icon: Icon(
                  _hide
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                  color: Colors.white70,
                ),
                onPressed: () => setState(() => _hide = !_hide),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceMd),
            GlassTextField(
              controller: _p2,
              label: 'Confirme a nova senha',
              obscureText: _hide,
              prefixIcon: const Icon(Icons.lock_outline,
                  color: Colors.white70, size: 20),
            ),
          ],
        ),
      ),
      bottom: Column(
        children: [
          GlassPrimaryButton(
            onPressed: _loading ? null : _submit,
            label: 'Redefinir senha',
            loading: _loading,
            icon: Icons.check_rounded,
          ),
          const SizedBox(height: BrandTokens.spaceXs),
        ],
      ),
    );
  }
}
