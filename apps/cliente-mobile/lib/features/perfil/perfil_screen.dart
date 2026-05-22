import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/contrato/contrato_atual_provider.dart';
import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/notifications/push_service.dart';
import '../../core/theme/theme_mode_controller.dart';
import '../../core/ui/formatters.dart';

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: meAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(child: Text('Erro carregando perfil')),
          data: (me) => ListView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            padding: const EdgeInsets.fromLTRB(
              BrandTokens.spaceLg,
              BrandTokens.spaceLg,
              BrandTokens.spaceLg,
              120,
            ),
            children: [
              _ProfileHeader(nome: me.nome, plano: me.planoNome),
              const SizedBox(height: BrandTokens.spaceLg),

              // Dados de contato
              _CardSection(
                title: 'Dados pessoais',
                children: [
                  _CardTile(
                    icon: Icons.badge_outlined,
                    iconColor: BrandTokens.catBilling,
                    label: 'CPF',
                    value: '***.***.***-${me.cpfLast4}',
                  ),
                  _CardTile(
                    icon: Icons.phone_outlined,
                    iconColor: BrandTokens.info,
                    label: 'Telefone',
                    value: formatTelefone(me.telefone),
                    onTap: () => context.push('/perfil/editar', extra: {
                      'campo': 'telefone',
                      'valor': me.telefone,
                    }),
                  ),
                  _CardTile(
                    icon: Icons.mail_outline,
                    iconColor: BrandTokens.catSupport,
                    label: 'Email',
                    value: (me.email ?? '').isEmpty
                        ? 'Não informado'
                        : me.email!,
                    onTap: () => context.push('/perfil/editar', extra: {
                      'campo': 'email',
                      'valor': me.email ?? '',
                    }),
                  ),
                ],
              ),

              // Seguranca
              _CardSection(
                title: 'Seguranca',
                children: [
                  _CardTile(
                    icon: Icons.lock_outline,
                    iconColor: BrandTokens.warning,
                    label: 'Mudar senha',
                    onTap: () => context.push('/perfil/mudar-senha'),
                  ),
                ],
              ),

              // Vantagens
              _CardSection(
                title: 'Vantagens',
                children: [
                  _CardTile(
                    icon: Icons.card_giftcard_rounded,
                    iconColor: BrandTokens.catPlan,
                    label: 'Indique e ganhe',
                    value: 'Compartilhe seu código e ganhe desconto',
                    onTap: () => context.push('/indicacao'),
                  ),
                ],
              ),

              // Aparencia (com toggle dark visivel)
              _CardSection(
                title: 'Aparencia',
                children: [
                  _ThemeTile(
                    currentMode: themeMode,
                    onChanged: (m) =>
                        ref.read(themeModeProvider.notifier).set(m),
                  ),
                ],
              ),

              // Sobre
              _CardSection(
                title: 'Sobre',
                children: [
                  _CardTile(
                    icon: Icons.description_outlined,
                    iconColor: BrandTokens.textSecondary,
                    label: 'Termos de Uso',
                    onTap: () => context.push('/legal/termos'),
                  ),
                  _CardTile(
                    icon: Icons.privacy_tip_outlined,
                    iconColor: BrandTokens.textSecondary,
                    label: 'Política de Privacidade',
                    onTap: () => context.push('/legal/privacidade'),
                  ),
                ],
              ),

              const SizedBox(height: BrandTokens.spaceLg),

              // Acoes finais
              SizedBox(
                height: 52,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('Sair'),
                  onPressed: () async {
                    // Limpa push token no backend ANTES do logout (precisa
                    // do token de auth ainda valido).
                    await ref.read(pushServiceProvider).clear();
                    await ref.read(authRepositoryProvider).logout();
                    // Limpa selecao de contrato pra nao vazar entre contas.
                    await ref.read(contratoAtualProvider.notifier).clear();
                    ref.read(authRefreshProvider).bump();
                    if (context.mounted) context.go('/onboarding/cpf');
                  },
                ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              TextButton(
                style: TextButton.styleFrom(
                  foregroundColor: BrandTokens.danger,
                  minimumSize: const Size.fromHeight(44),
                ),
                onPressed: () => _confirmDelete(context, ref),
                child: const Text(
                  'Excluir minha conta',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ════════ Header com avatar gradient + nome + plano ════════

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.nome, required this.plano});
  final String nome;
  final String? plano;

  String _initials(String full) {
    final parts = full.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Avatar circular gradient + ring
        Container(
          width: 104,
          height: 104,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: BrandTokens.gradientHero,
            boxShadow: BrandTokens.shadowColored,
          ),
          alignment: Alignment.center,
          child: Text(
            _initials(nome),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 38,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.5,
            ),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceMd),
        Text(
          nome.isEmpty ? 'Cliente' : nome,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
        ),
        if (plano != null && plano!.isNotEmpty) ...[
          const SizedBox(height: BrandTokens.spaceXs),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: 6,
            ),
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.wifi_rounded,
                    size: 14, color: BrandTokens.primary),
                const SizedBox(width: 6),
                Text(
                  plano!,
                  style: const TextStyle(
                    color: BrandTokens.primary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

// ════════ Card agrupado ════════

class _CardSection extends StatelessWidget {
  const _CardSection({required this.title, required this.children});
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.only(
              left: BrandTokens.spaceXs,
              bottom: BrandTokens.spaceSm,
            ),
            child: Text(
              title.toUpperCase(),
              style: const TextStyle(
                color: BrandTokens.textSecondary,
                fontWeight: FontWeight.w800,
                fontSize: 11,
                letterSpacing: 1.2,
              ),
            ),
          ),
          Container(
            decoration: BoxDecoration(
              color: isDark
                  ? BrandTokens.surfaceDark
                  : BrandTokens.surface,
              borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              border: Border.all(
                color: isDark ? Colors.white12 : BrandTokens.divider,
              ),
              boxShadow: BrandTokens.elevation1,
            ),
            child: Column(
              children: [
                for (int i = 0; i < children.length; i++) ...[
                  children[i],
                  if (i < children.length - 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: BrandTokens.spaceMd,
                      ),
                      child: Divider(
                        height: 1,
                        thickness: 1,
                        color: isDark ? Colors.white10 : BrandTokens.divider,
                      ),
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CardTile extends StatelessWidget {
  const _CardTile({
    required this.icon,
    required this.iconColor,
    required this.label,
    this.value,
    this.onTap,
  });
  final IconData icon;
  final Color iconColor;
  final String label;
  final String? value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: iconColor.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: Icon(icon, color: iconColor, size: 20),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                      ),
                    ),
                    if (value != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        value!,
                        style: const TextStyle(
                          color: BrandTokens.textSecondary,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              if (onTap != null)
                const Icon(
                  Icons.chevron_right_rounded,
                  color: BrandTokens.textSecondary,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ════════ Toggle tema visivel ════════

class _ThemeTile extends StatelessWidget {
  const _ThemeTile({required this.currentMode, required this.onChanged});
  final ThemeMode currentMode;
  final ValueChanged<ThemeMode> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: BrandTokens.info.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: const Icon(
                  Icons.brightness_6_outlined,
                  color: BrandTokens.info,
                  size: 20,
                ),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              const Expanded(
                child: Text(
                  'Tema',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          _SegmentedTheme(current: currentMode, onChanged: onChanged),
        ],
      ),
    );
  }
}

class _SegmentedTheme extends StatelessWidget {
  const _SegmentedTheme({required this.current, required this.onChanged});
  final ThemeMode current;
  final ValueChanged<ThemeMode> onChanged;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? Colors.white10 : BrandTokens.background;
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Row(
        children: [
          _Seg(
            label: 'Auto',
            icon: Icons.brightness_auto_rounded,
            selected: current == ThemeMode.system,
            onTap: () => onChanged(ThemeMode.system),
          ),
          _Seg(
            label: 'Claro',
            icon: Icons.light_mode_rounded,
            selected: current == ThemeMode.light,
            onTap: () => onChanged(ThemeMode.light),
          ),
          _Seg(
            label: 'Escuro',
            icon: Icons.dark_mode_rounded,
            selected: current == ThemeMode.dark,
            onTap: () => onChanged(ThemeMode.dark),
          ),
        ],
      ),
    );
  }
}

class _Seg extends StatelessWidget {
  const _Seg({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
          child: AnimatedContainer(
            duration: BrandTokens.motionFast,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: selected
                  ? (isDark ? BrandTokens.surfaceDark : BrandTokens.surface)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
              boxShadow: selected ? BrandTokens.elevation1 : null,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  icon,
                  size: 18,
                  color: selected
                      ? BrandTokens.primary
                      : BrandTokens.textSecondary,
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: TextStyle(
                    fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                    fontSize: 11,
                    color: selected
                        ? BrandTokens.primary
                        : BrandTokens.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ════════ Confirm exclusao ════════

Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Excluir minha conta?'),
      content: const Text(
        'Esta ação e definitiva. Seu acesso ao app será revogado e seus dados pessoais anonimizados.\n\nVoce continua sendo cliente da Ondeline e podera criar uma nova conta no app a qualquer momento.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        TextButton(
          style: TextButton.styleFrom(foregroundColor: BrandTokens.danger),
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Excluir'),
        ),
      ],
    ),
  );
  if (ok != true) return;

  // Limpa push token antes do delete (deleteMe ja anonimiza no backend mas
  // limpamos no FCM tambem pra parar mensagens fantasma no device).
  await ref.read(pushServiceProvider).clear();
  final success = await ref.read(meRepositoryProvider).deleteMe();
  if (!context.mounted) return;
  if (success) {
    await ref.read(authRepositoryProvider).logout();
    await ref.read(contratoAtualProvider.notifier).clear();
    ref.read(authRefreshProvider).bump();
    if (context.mounted) context.go('/onboarding/cpf');
  } else {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Falha ao excluir. Tente de novo.')),
    );
  }
}
