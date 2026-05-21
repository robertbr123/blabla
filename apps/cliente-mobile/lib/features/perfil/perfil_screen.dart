import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/dev/dev_mode.dart';
import '../../core/theme/theme_mode_controller.dart';

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Perfil')),
      body: meAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Erro carregando perfil')),
        data: (me) => ListView(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          children: [
            _Avatar(nome: me.nome),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              me.nome.isEmpty ? 'Cliente' : me.nome,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            Text(
              'CPF ***.***.***-${me.cpfLast4}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceXl),
            _Section(title: 'Dados de contato', children: [
              _Tile(
                icon: Icons.phone_outlined,
                label: 'Telefone',
                value: me.telefone,
                onTap: () => context.push('/perfil/editar', extra: {
                  'campo': 'telefone',
                  'valor': me.telefone,
                }),
              ),
              _Tile(
                icon: Icons.mail_outline,
                label: 'Email',
                value: me.email ?? 'Nao informado',
                onTap: () => context.push('/perfil/editar', extra: {
                  'campo': 'email',
                  'valor': me.email ?? '',
                }),
              ),
            ]),
            _Section(title: 'Seguranca', children: [
              _Tile(
                icon: Icons.lock_outline,
                label: 'Mudar senha',
                onTap: () => context.push('/perfil/mudar-senha'),
              ),
            ]),
            _Section(title: 'Aparencia', children: [
              ListTile(
                leading: const Icon(Icons.brightness_6_outlined),
                title: const Text('Tema'),
                trailing: DropdownButton<ThemeMode>(
                  value: themeMode,
                  underline: const SizedBox.shrink(),
                  onChanged: (m) {
                    if (m != null) {
                      ref.read(themeModeProvider.notifier).set(m);
                    }
                  },
                  items: const [
                    DropdownMenuItem(
                        value: ThemeMode.system, child: Text('Automatico')),
                    DropdownMenuItem(
                        value: ThemeMode.light, child: Text('Claro')),
                    DropdownMenuItem(
                        value: ThemeMode.dark, child: Text('Escuro')),
                  ],
                ),
              ),
            ]),
            const SizedBox(height: BrandTokens.spaceLg),
            OutlinedButton.icon(
              icon: const Icon(Icons.logout),
              label: const Text('Sair'),
              onPressed: () async {
                await ref.read(devModeProvider).disable();
                await ref.read(authRepositoryProvider).logout();
                ref.read(authRefreshProvider).bump();
                if (context.mounted) context.go('/onboarding/cpf');
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.nome});
  final String nome;

  @override
  Widget build(BuildContext context) {
    final initials = _initials(nome);
    return Center(
      child: Container(
        width: 96,
        height: 96,
        decoration: BoxDecoration(
          color: BrandTokens.primary.withOpacity(0.10),
          borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
        ),
        alignment: Alignment.center,
        child: Text(
          initials,
          style: const TextStyle(
            fontSize: 32,
            fontWeight: FontWeight.w800,
            color: BrandTokens.primary,
          ),
        ),
      ),
    );
  }

  String _initials(String full) {
    final parts = full.trim().split(' ').where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(
            top: BrandTokens.spaceLg,
            bottom: BrandTokens.spaceSm,
          ),
          child: Text(
            title,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: BrandTokens.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    this.value,
    this.onTap,
  });
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      subtitle: value == null ? null : Text(value!),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
