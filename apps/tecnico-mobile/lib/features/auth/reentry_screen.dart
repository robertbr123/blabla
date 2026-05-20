import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/biometric_service.dart';

class ReentryScreen extends ConsumerStatefulWidget {
  const ReentryScreen({super.key});

  @override
  ConsumerState<ReentryScreen> createState() => _ReentryScreenState();
}

class _ReentryScreenState extends ConsumerState<ReentryScreen> {
  bool _loading = false;

  Future<void> _authenticate() async {
    setState(() => _loading = true);
    try {
      final ok = await ref.read(biometricServiceProvider).authenticate();
      if (!mounted) return;
      if (ok) {
        context.go('/os');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Não consegui validar o Face ID.')),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Face ID indisponível no momento.')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final sessionAsync = ref.watch(sessionSnapshotProvider);

    return Scaffold(
      backgroundColor: scheme.surface,
      body: SafeArea(
        child: sessionAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) context.go('/os');
            });
            return const Center(child: CircularProgressIndicator());
          },
          data: (session) {
            if (session == null) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (mounted) context.go('/os');
              });
              return const Center(child: CircularProgressIndicator());
            }

            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Icon(
                        Icons.face_retouching_natural,
                        size: 72,
                        color: scheme.primary,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        session.nome,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          color: scheme.onSurface,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Entre rapidamente no app com Face ID.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 14,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 28),
                      FilledButton.icon(
                        onPressed: _loading ? null : _authenticate,
                        icon: const Icon(Icons.face),
                        label: _loading
                            ? const SizedBox(
                                height: 18,
                                width: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Text('Entrar com Face ID'),
                      ),
                      const SizedBox(height: 12),
                      TextButton(
                        onPressed: _loading ? null : () => context.go('/login'),
                        child: const Text('Entrar com email e senha'),
                      ),
                    ],
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
