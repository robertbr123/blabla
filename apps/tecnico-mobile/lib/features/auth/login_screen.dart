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
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Stack(
                children: [
                  Positioned(
                    top: 24,
                    right: 8,
                    child: _AmbientGlow(
                      color: scheme.primary.withValues(alpha: 0.18),
                      size: 168,
                    ),
                  ),
                  Positioned(
                    top: 120,
                    left: -12,
                    child: _AmbientGlow(
                      color: scheme.secondary.withValues(alpha: 0.12),
                      size: 132,
                    ),
                  ),
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              scheme.surface,
                              scheme.surfaceContainerLow,
                            ],
                          ),
                          borderRadius: BorderRadius.circular(32),
                          border: Border.all(
                            color:
                                scheme.outlineVariant.withValues(alpha: 0.65),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: scheme.shadow.withValues(alpha: 0.08),
                              blurRadius: 28,
                              offset: const Offset(0, 20),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color: scheme.primaryContainer
                                    .withValues(alpha: 0.9),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                'LOGIN SEGURO',
                                style: TextStyle(
                                  fontSize: 11,
                                  letterSpacing: 1.6,
                                  fontWeight: FontWeight.w800,
                                  color: scheme.onPrimaryContainer,
                                ),
                              ),
                            ),
                            const SizedBox(height: 20),
                            Center(
                              child: Image.asset(
                                Theme.of(context).brightness == Brightness.dark
                                    ? 'assets/branding/logo_horizontal_dark.png'
                                    : 'assets/branding/logo_horizontal_light.png',
                                height: 88,
                                fit: BoxFit.contain,
                              ),
                            ),
                            const SizedBox(height: 20),
                            Text(
                              'Painel técnico em campo',
                              style: TextStyle(
                                fontSize: 30,
                                height: 1.05,
                                fontWeight: FontWeight.w900,
                                color: scheme.onSurface,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              'Atendimentos, estoque e sync offline sem fricção.',
                              style: TextStyle(
                                fontSize: 15,
                                height: 1.45,
                                color: scheme.onSurfaceVariant,
                              ),
                            ),
                            const SizedBox(height: 18),
                            const Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: [
                                _LoginHighlight(
                                  icon: Icons.wifi_off_rounded,
                                  label: 'Fluxo offline pronto',
                                ),
                                _LoginHighlight(
                                  icon: Icons.inventory_2_outlined,
                                  label: 'Estoque no aparelho',
                                ),
                                _LoginHighlight(
                                  icon: Icons.lock_outline_rounded,
                                  label: 'Reentrada com Face ID',
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      Container(
                        padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
                        decoration: BoxDecoration(
                          color: scheme.surface,
                          borderRadius: BorderRadius.circular(28),
                          border: Border.all(
                            color: scheme.outlineVariant.withValues(alpha: 0.7),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: scheme.shadow.withValues(alpha: 0.06),
                              blurRadius: 20,
                              offset: const Offset(0, 12),
                            ),
                          ],
                        ),
                        child: AutofillGroup(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    height: 42,
                                    width: 42,
                                    decoration: BoxDecoration(
                                      color: scheme.surfaceContainer,
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                    child: Icon(
                                      Icons.badge_outlined,
                                      color: scheme.primary,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'Acesso do técnico',
                                          style: TextStyle(
                                            fontSize: 17,
                                            fontWeight: FontWeight.w800,
                                            color: scheme.onSurface,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          'Entre com sua conta corporativa.',
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: scheme.onSurfaceVariant,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 20),
                              TextField(
                                controller: _email,
                                keyboardType: TextInputType.emailAddress,
                                autofillHints: const [AutofillHints.username],
                                decoration: InputDecoration(
                                  labelText: 'Email corporativo',
                                  hintText: 'voce@empresa.com',
                                  prefixIcon: const Icon(Icons.email_outlined),
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(18),
                                  ),
                                ),
                                textInputAction: TextInputAction.next,
                              ),
                              const SizedBox(height: 14),
                              TextField(
                                controller: _senha,
                                obscureText: !_mostrarSenha,
                                autofillHints: const [AutofillHints.password],
                                decoration: InputDecoration(
                                  labelText: 'Senha',
                                  prefixIcon: const Icon(Icons.lock_outline),
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _mostrarSenha
                                          ? Icons.visibility_off_outlined
                                          : Icons.visibility_outlined,
                                    ),
                                    onPressed: () => setState(
                                      () => _mostrarSenha = !_mostrarSenha,
                                    ),
                                  ),
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(18),
                                  ),
                                ),
                                onSubmitted: (_) => _entrar(),
                              ),
                              if (_erro != null) ...[
                                const SizedBox(height: 12),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: scheme.errorContainer
                                        .withValues(alpha: 0.7),
                                    borderRadius: BorderRadius.circular(16),
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
                                            color: scheme.onErrorContainer,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              const SizedBox(height: 18),
                              FilledButton(
                                onPressed: _loading ? null : _entrar,
                                style: FilledButton.styleFrom(
                                  minimumSize: const Size.fromHeight(56),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(18),
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
                              const SizedBox(height: 12),
                              Text(
                                'Depois do primeiro acesso, a reentrada pode ser feita com Face ID no iPhone.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 12,
                                  height: 1.4,
                                  color: scheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Center(
                        child: Text(
                          'Linket · app técnico',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color:
                                scheme.onSurfaceVariant.withValues(alpha: 0.75),
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
      ),
    );
  }
}

class _LoginHighlight extends StatelessWidget {
  const _LoginHighlight({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: scheme.surface.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.7)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: scheme.primary),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: scheme.onSurface,
            ),
          ),
        ],
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
