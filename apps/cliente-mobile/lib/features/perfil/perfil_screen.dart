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
import '../../core/ui/capa_folha.dart';
import '../../core/ui/formatters.dart';

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final themeMode = ref.watch(themeModeProvider);
    final topInset = MediaQuery.paddingOf(context).top;
    final screenHeight = MediaQuery.sizeOf(context).height;

    return Scaffold(
      body: meAsync.when(
        loading: () => CustomScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          slivers: [
            SliverPersistentHeader(
              pinned: true,
              delegate: _PerfilCapaDelegate(topInset: topInset, loading: true),
            ),
            _folhaFiller(
              context,
              minHeight: screenHeight,
              child: const SizedBox.shrink(),
            ),
          ],
        ),
        error: (_, __) => CustomScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          slivers: [
            SliverPersistentHeader(
              pinned: true,
              delegate:
                  _PerfilCapaDelegate(topInset: topInset, errorMode: true),
            ),
            _folhaFiller(
              context,
              minHeight: screenHeight,
              child: const Center(child: Text('Erro carregando perfil')),
            ),
          ],
        ),
        data: (me) => CustomScrollView(
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          slivers: [
            SliverPersistentHeader(
              pinned: true,
              delegate: _PerfilCapaDelegate(
                topInset: topInset,
                nome: me.nome,
                plano: me.planoNome,
              ),
            ),
            _folhaFiller(
              context,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  BrandTokens.spaceLg,
                  BrandTokens.spaceLg,
                  BrandTokens.spaceLg,
                  120,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
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
                          icon: Icons.workspace_premium_rounded,
                          iconColor: BrandTokens.warning,
                          label: 'Programa de fidelidade',
                          value: 'Acumule pontos e troque por descontos',
                          onTap: () => context.push('/fidelidade'),
                        ),
                        _CardTile(
                          icon: Icons.card_giftcard_rounded,
                          iconColor: BrandTokens.catPlan,
                          label: 'Indique e ganhe',
                          value: 'Compartilhe seu código e ganhe desconto',
                          onTap: () => context.push('/indicacao'),
                        ),
                      ],
                    ),

                    // Atendimento
                    _CardSection(
                      title: 'Atendimento',
                      children: [
                        _CardTile(
                          icon: Icons.contact_phone_outlined,
                          iconColor: BrandTokens.primary,
                          label: 'Fale conosco',
                          value: 'WhatsApp, telefone, endereço e redes',
                          onTap: () => context.push('/contatos'),
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
                          await ref
                              .read(contratoAtualProvider.notifier)
                              .clear();
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
          ],
        ),
      ),
    );
  }
}

// ════════ Sliver com o "canto" da capa por trás da folha ════════
//
// Sem o overlap/Transform do FolhaContainer (fonte do corte azul sob
// scroll): aqui a folha nasce dentro de um Container pintado com o tom
// final do gradiente da capa (capaDeep), então os cantos arredondados da
// folha revelam sempre a mesma cor da capa por baixo — nunca uma fresta.
Widget _folhaFiller(
  BuildContext context, {
  required Widget child,
  double minHeight = 0,
}) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  return SliverToBoxAdapter(
    child: Container(
      color: BrandTokens.capaDeep,
      child: Container(
        constraints: BoxConstraints(minHeight: minHeight),
        decoration: BoxDecoration(
          color: isDark ? BrandTokens.backgroundDark : BrandTokens.background,
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(BrandTokens.radiusFolha),
          ),
        ),
        child: child,
      ),
    ),
  );
}

// ════════ Header colapsavel: avatar+nome fixos ao rolar ════════

class _PerfilCapaDelegate extends SliverPersistentHeaderDelegate {
  const _PerfilCapaDelegate({
    required this.topInset,
    this.nome,
    this.plano,
    this.loading = false,
    this.errorMode = false,
  });

  final double topInset;
  final String? nome;
  final String? plano;
  final bool loading;
  final bool errorMode;

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  String _initials(String full) {
    final parts =
        full.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  @override
  double get maxExtent => topInset + 210;

  @override
  double get minExtent => topInset + 64;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    final range = maxExtent - minExtent;
    final t = range <= 0 ? 0.0 : (shrinkOffset / range).clamp(0.0, 1.0);

    Widget content;
    if (loading) {
      content = const Center(
        child: CircularProgressIndicator(color: Colors.white),
      );
    } else if (errorMode) {
      content = Padding(
        padding: EdgeInsets.only(
          left: BrandTokens.spaceLg,
          right: BrandTokens.spaceLg,
          top: topInset + BrandTokens.spaceMd,
        ),
        child: Align(
          alignment: Alignment.topLeft,
          child: Text(
            'Perfil',
            style: TextStyle(
              color: BrandTokens.capaInk,
              fontSize: _lerp(24, 18, t),
              fontWeight: FontWeight.w900,
              letterSpacing: -0.6,
            ),
          ),
        ),
      );
    } else {
      final displayNome = (nome == null || nome!.isEmpty) ? 'Cliente' : nome!;
      final displayPlano = plano;
      content = LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final avatarSize = _lerp(72, 28, t);
          final avatarLeft = _lerp((width - 72) / 2, BrandTokens.spaceLg, t);
          final avatarTop = _lerp(
            topInset + BrandTokens.spaceLg,
            topInset + (64 - 28) / 2,
            t,
          );
          final nomeLeft = _lerp(
            0,
            avatarLeft + avatarSize + BrandTokens.spaceMd,
            t,
          );
          final nomeRightPad = _lerp(0, BrandTokens.spaceLg, t);
          final nomeWidth = (width - nomeLeft - nomeRightPad).clamp(
            0.0,
            width,
          );
          final nomeTop = _lerp(
            avatarTop + 72 + BrandTokens.spaceMd,
            avatarTop + (28 - 20) / 2,
            t,
          );
          final planoOpacity = (1 - t * 2).clamp(0.0, 1.0);

          return Stack(
            children: [
              Positioned(
                left: avatarLeft,
                top: avatarTop,
                width: avatarSize,
                height: avatarSize,
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withValues(alpha: 0.25),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    _initials(displayNome),
                    style: TextStyle(
                      color: BrandTokens.capaInk,
                      fontSize: _lerp(26, 13, t),
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ),
              Positioned(
                left: nomeLeft,
                top: nomeTop,
                width: nomeWidth,
                child: Text(
                  displayNome,
                  textAlign: t < 0.5 ? TextAlign.center : TextAlign.left,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: BrandTokens.capaInk,
                    fontSize: _lerp(26, 16, t),
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.8,
                    height: 1.1,
                  ),
                ),
              ),
              if (displayPlano != null && displayPlano.isNotEmpty)
                Positioned(
                  left: 0,
                  right: 0,
                  top: avatarTop + avatarSize + BrandTokens.spaceXs,
                  child: Opacity(
                    opacity: planoOpacity,
                    child: Text(
                      displayPlano,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: BrandTokens.capaInk.withValues(alpha: 0.7),
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      );
    }

    return ClipRect(
      child: SizedBox.expand(
        child: CapaBackground(padding: EdgeInsets.zero, child: content),
      ),
    );
  }

  @override
  bool shouldRebuild(covariant _PerfilCapaDelegate oldDelegate) {
    return oldDelegate.topInset != topInset ||
        oldDelegate.nome != nome ||
        oldDelegate.plano != plano ||
        oldDelegate.loading != loading ||
        oldDelegate.errorMode != errorMode;
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
              color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
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
