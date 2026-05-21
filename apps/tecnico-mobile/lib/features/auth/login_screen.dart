import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/auth/biometric_service.dart';
import '../../core/push/fcm_service.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _senha = TextEditingController();
  bool _loading = false;
  bool _mostrarSenha = false;
  String? _erro;

  @override
  void dispose() {
    _email.dispose();
    _senha.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    setState(() {
      _loading = true;
      _erro = null;
    });
    try {
      final result = await ref
          .read(authRepositoryProvider)
          .login(_email.text.trim(), _senha.text);
      final canUseBiometrics =
          await ref.read(biometricServiceProvider).canUseBiometrics();
      await saveSessionSnapshot(
        userId: result.userId,
        role: result.role,
        nome: resolveLoginDisplayName(
          email: _email.text.trim(),
          loginResult: result,
        ),
        biometricEnabled: canUseBiometrics,
      );
      ref.invalidate(hasTokenProvider);
      ref.invalidate(sessionSnapshotProvider);
      if (Firebase.apps.isNotEmpty) {
        unawaited(ref.read(fcmServiceProvider).init());
      }
      if (!mounted) return;
      context.go('/os');
    } catch (e) {
      setState(() => _erro = 'Não consegui entrar. Confere email e senha.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 440),
                    child: Stack(
                      children: [
                        Positioned(
                          top: 18,
                          right: 4,
                          child: _AmbientGlow(
                            color: scheme.primary.withValues(alpha: 0.16),
                            size: 148,
                          ),
                        ),
                        Positioned(
                          top: 92,
                          left: -8,
                          child: _AmbientGlow(
                            color: scheme.secondary.withValues(alpha: 0.1),
                            size: 112,
                          ),
                        ),
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const SizedBox(height: 20),
                            // Logo centralizado, sem card e sem highlights — versão enxuta.
                            Center(
                              child: Image.asset(
                                Theme.of(context).brightness == Brightness.dark
                                    ? 'assets/branding/logo_horizontal_dark.png'
                                    : 'assets/branding/logo_horizontal_light.png',
                                height: 56,
                                fit: BoxFit.contain,
                              ),
                            ),
                            const SizedBox(height: 24),
                            Container(
                              padding:
                                  const EdgeInsets.fromLTRB(18, 18, 18, 16),
                              decoration: BoxDecoration(
                                color: scheme.surface,
                                borderRadius: BorderRadius.circular(24),
                                border: Border.all(
                                  color: scheme.outlineVariant
                                      .withValues(alpha: 0.7),
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color:
                                        scheme.shadow.withValues(alpha: 0.06),
                                    blurRadius: 18,
                                    offset: const Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: AutofillGroup(
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    TextField(
                                      controller: _email,
                                      keyboardType: TextInputType.emailAddress,
                                      autofillHints: const [
                                        AutofillHints.username,
                                      ],
                                      decoration: InputDecoration(
                                        labelText: 'Email corporativo',
                                        hintText: 'voce@empresa.com',
                                        prefixIcon:
                                            const Icon(Icons.email_outlined),
                                        border: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(18),
                                        ),
                                      ),
                                      textInputAction: TextInputAction.next,
                                    ),
                                    const SizedBox(height: 12),
                                    TextField(
                                      controller: _senha,
                                      obscureText: !_mostrarSenha,
                                      autofillHints: const [
                                        AutofillHints.password,
                                      ],
                                      decoration: InputDecoration(
                                        labelText: 'Senha',
                                        prefixIcon:
                                            const Icon(Icons.lock_outline),
                                        suffixIcon: IconButton(
                                          icon: Icon(
                                            _mostrarSenha
                                                ? Icons.visibility_off_outlined
                                                : Icons.visibility_outlined,
                                          ),
                                          onPressed: () => setState(
                                            () =>
                                                _mostrarSenha = !_mostrarSenha,
                                          ),
                                        ),
                                        border: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(18),
                                        ),
                                      ),
                                      onSubmitted: (_) => _entrar(),
                                    ),
                                    if (_erro != null) ...[
                                      const SizedBox(height: 10),
                                      Container(
                                        padding: const EdgeInsets.all(10),
                                        decoration: BoxDecoration(
                                          color: scheme.errorContainer
                                              .withValues(alpha: 0.7),
                                          borderRadius:
                                              BorderRadius.circular(16),
                                        ),
                                        child: Row(
                                          children: [
                                            Icon(
                                              Icons.error_outline,
                                              size: 18,
                                              color: scheme.error,
                                            ),
                                            const SizedBox(width: 8),
                                            Expanded(
                                              child: Text(
                                                _erro!,
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  color:
                                                      scheme.onErrorContainer,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                    const SizedBox(height: 14),
                                    FilledButton(
                                      onPressed: _loading ? null : _entrar,
                                      style: FilledButton.styleFrom(
                                        minimumSize: const Size.fromHeight(52),
                                        shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(18),
                                        ),
                                      ),
                                      child: _loading
                                          ? const SizedBox(
                                              height: 20,
                                              width: 20,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                                color: Colors.white,
                                              ),
                                            )
                                          : const Text(
                                              'Acessar painel',
                                              style: TextStyle(
                                                fontSize: 15,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                    ),
                                    const SizedBox(height: 10),
                                    Text(
                                      'Depois do primeiro acesso, a reentrada pode ser feita com Face ID no iPhone.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        fontSize: 11,
                                        height: 1.3,
                                        color: scheme.onSurfaceVariant,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Center(
                              child: Text(
                                'BlaBla · app técnico',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: scheme.onSurfaceVariant
                                      .withValues(alpha: 0.7),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _AmbientGlow extends StatelessWidget {
  const _AmbientGlow({
    required this.color,
    required this.size,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              color,
              color.withValues(alpha: 0),
            ],
          ),
        ),
      ),
    );
  }
}
