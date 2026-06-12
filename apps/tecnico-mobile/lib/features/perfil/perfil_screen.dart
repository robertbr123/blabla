import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/session_cleanup.dart';
import '../../core/branding/brand_kpi_card.dart';
import '../../core/branding/brand_status_pill.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/push/fcm_service.dart';
import '../../core/ui/app_state_panel.dart';
import '../os/widgets/cliente_avatar.dart';
import 'perfil_data.dart';

// Estado do easter egg da versão — 3 taps em <1.2s revelam o autor.
int _versionTapCount = 0;
DateTime? _versionFirstTap;

void _maybeRevealEasterEgg(BuildContext context) {
  final now = DateTime.now();
  if (_versionFirstTap == null ||
      now.difference(_versionFirstTap!) > const Duration(milliseconds: 1200)) {
    _versionFirstTap = now;
    _versionTapCount = 1;
    return;
  }
  _versionTapCount++;
  if (_versionTapCount >= 3) {
    _versionTapCount = 0;
    _versionFirstTap = null;
    showDialog<void>(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.7),
      builder: (_) => const _AutorEasterEggDialog(),
    );
  }
}

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(perfilProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surface,
      appBar: AppBar(
        toolbarHeight: 48,
        backgroundColor: scheme.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar',
            onPressed: () => ref.invalidate(perfilProvider),
          ),
        ],
      ),
      body: async.when(
        loading: () => const _StateBody(
          child: AppStatePanel.loading(
            title: 'Carregando seu perfil',
            message: 'Preparando foto, status e estatísticas.',
          ),
        ),
        error: (e, _) => _ErroView(
          e: e,
          onRetry: () => ref.invalidate(perfilProvider),
        ),
        data: (p) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(perfilProvider),
          child: ListView(
            // Bottom extra pra ultima opcao nao ficar atras do navbar flutuante
            // (Scaffold usa extendBody: navbar 60 + margens 14 + safe area).
            padding: EdgeInsets.fromLTRB(
              16,
              12,
              16,
              32 + 74 + MediaQuery.paddingOf(context).bottom,
            ),
            children: [
              _Header(perfil: p),
              const SizedBox(height: 20),
              const _SectionTitle('Atividade do mês'),
              const SizedBox(height: 8),
              _StatsGrid(stats: p.estatisticas),
              const SizedBox(height: 20),
              const _SectionTitle('Conta'),
              const SizedBox(height: 8),
              _ActionTile(
                icon: Icons.lock_outline,
                title: 'Mudar senha',
                onTap: () => _openMudarSenha(context),
              ),
              const SizedBox(height: 8),
              _ActionTile(
                icon: Icons.logout,
                title: 'Sair',
                destructive: true,
                onTap: () => _logout(context, ref),
              ),
              const SizedBox(height: 20),
              const _SectionTitle('Sobre'),
              const SizedBox(height: 8),
              _InfoTile(
                icon: Icons.smartphone,
                label: 'Versão',
                value: '0.1.0',
                onTap: () => _maybeRevealEasterEgg(context),
              ),
              const SizedBox(height: 8),
              const _InfoTile(icon: Icons.business, label: 'Empresa', value: 'Linket'),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _openMudarSenha(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _MudarSenhaSheet(),
    );
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final confirma = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sair?'),
        content: const Text(
          'Você terá que fazer login de novo pra acessar o app.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Sair'),
          ),
        ],
      ),
    );
    if (confirma != true) return;
    try {
      await ref.read(fcmServiceProvider).revoke();
    } catch (_) {}
    await ref.read(authRepositoryProvider).logout();
    await ref.read(sessionCleanupProvider).clearLocalSession();
    if (context.mounted) context.go('/login');
  }
}

// ── Header ──────────────────────────────────────────────────

class _Header extends ConsumerStatefulWidget {
  final Perfil perfil;
  const _Header({required this.perfil});

  @override
  ConsumerState<_Header> createState() => _HeaderState();
}

enum _PhotoAction { camera, gallery, remove }

class _HeaderState extends ConsumerState<_Header> {
  bool _uploading = false;

  Future<void> _changePhoto() async {
    final action = await showModalBottomSheet<_PhotoAction>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera),
              title: const Text('Tirar foto'),
              onTap: () => Navigator.of(context).pop(_PhotoAction.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Escolher da galeria'),
              onTap: () => Navigator.of(context).pop(_PhotoAction.gallery),
            ),
            if (widget.perfil.hasFoto)
              ListTile(
                leading: Icon(Icons.delete_outline,
                    color: Theme.of(context).colorScheme.error),
                title: Text('Remover foto atual',
                    style: TextStyle(
                        color: Theme.of(context).colorScheme.error)),
                onTap: () => Navigator.of(context).pop(_PhotoAction.remove),
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (action == null || !mounted) return;

    if (action == _PhotoAction.remove) {
      setState(() => _uploading = true);
      try {
        await ref.read(perfilActionsProvider).removerFoto();
        ref.invalidate(perfilProvider);
        _toast('Foto removida.');
      } finally {
        if (mounted) setState(() => _uploading = false);
      }
      return;
    }

    final source = action == _PhotoAction.camera
        ? ImageSource.camera
        : ImageSource.gallery;
    final x = await ImagePicker()
        .pickImage(source: source, imageQuality: 90, maxWidth: 1200);
    if (x == null || !mounted) return;
    setState(() => _uploading = true);
    try {
      await ref.read(perfilActionsProvider).uploadFoto(x.path);
      ref.invalidate(perfilProvider);
      _toast('Foto atualizada.');
    } on DioException catch (e) {
      final data = e.response?.data;
      final detail = data is Map ? data['detail']?.toString() : null;
      _toast(detail != null && detail.trim().isNotEmpty
          ? detail
          : (e.type == DioExceptionType.connectionError
              ? 'Sem conexão pra enviar a foto. Tente de novo.'
              : 'Não foi possível atualizar a foto. Tente de novo.'));
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  void _toast(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final p = widget.perfil;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          button: true,
          enabled: !_uploading,
          label: 'Alterar foto de perfil',
          child: Stack(
          children: [
            GestureDetector(
              onTap: _uploading ? null : _changePhoto,
              child: ClipOval(
                child: SizedBox(
                  width: 72,
                  height: 72,
                  child: p.hasFoto
                      ? Image.memory(
                          base64Decode(p.fotoB64!),
                          width: 72,
                          height: 72,
                          fit: BoxFit.cover,
                        )
                      : ClienteAvatar(nome: p.nome, size: 72),
                ),
              ),
            ),
            Positioned(
              right: 0,
              bottom: 0,
              child: GestureDetector(
                onTap: _uploading ? null : _changePhoto,
                child: Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: scheme.primary,
                    shape: BoxShape.circle,
                    border: Border.all(color: scheme.surface, width: 2),
                  ),
                  child: _uploading
                      ? const SizedBox(
                          height: 12,
                          width: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.camera_alt,
                          size: 14, color: Colors.white),
                ),
              ),
            ),
          ],
        ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                p.nome,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: scheme.onSurface,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 6),
              _ContactRow(icon: Icons.email_outlined, value: p.email),
              if (p.contatoWhatsapp != null) ...[
                const SizedBox(height: 2),
                _ContactRow(icon: Icons.phone_iphone, value: p.contatoWhatsapp!),
              ],
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  BrandStatusPill(
                    label: p.availabilityLabel,
                    icon: p.ativo
                        ? Icons.check_circle_outline
                        : Icons.pause_circle_outline,
                    tone: p.ativo ? BrandTone.success : BrandTone.warning,
                    size: BrandPillSize.sm,
                  ),
                  BrandStatusPill(
                    label: p.roleLabel,
                    icon: Icons.badge_outlined,
                    tone: BrandTone.info,
                    size: BrandPillSize.sm,
                  ),
                  if (p.hasRecentGpsSnapshot())
                    const BrandStatusPill(
                      label: 'GPS recente',
                      icon: Icons.location_on_outlined,
                      tone: BrandTone.neutral,
                      size: BrandPillSize.sm,
                    ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Stats ───────────────────────────────────────────────────

class _StatsGrid extends StatelessWidget {
  final PerfilEstatisticas stats;
  const _StatsGrid({required this.stats});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: BrandKpiCard(
                label: 'Pendentes',
                value: '${stats.osPendentes}',
                icon: Icons.hourglass_top_outlined,
                tone: BrandTone.warning,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: BrandKpiCard(
                label: 'Em andamento',
                value: '${stats.osEmAndamento}',
                icon: Icons.directions_run,
                tone: BrandTone.info,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: BrandKpiCard(
                label: 'Concluídas (mês)',
                value: '${stats.osConcluidasMes}',
                icon: Icons.check_circle_outline,
                tone: BrandTone.success,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: BrandKpiCard(
                label: 'CSAT médio',
                value: stats.csatAvgMes != null
                    ? stats.csatAvgMes!.toStringAsFixed(1)
                    : '—',
                icon: Icons.star_outline,
                tone: BrandTone.success,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ── Reusable bits ───────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.6,
        color: scheme.onSurfaceVariant,
      ),
    );
  }
}

class _ContactRow extends StatelessWidget {
  final IconData icon;
  final String value;
  const _ContactRow({required this.icon, required this.value});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, size: 13, color: scheme.onSurfaceVariant),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            value,
            style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;
  final bool destructive;
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.onTap,
    this.destructive = false,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = destructive ? scheme.error : scheme.onSurface;
    return Material(
      color: scheme.surfaceContainer,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: scheme.outlineVariant),
          ),
          child: Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, size: 18, color: color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                ),
              ),
              Icon(Icons.chevron_right, color: scheme.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final VoidCallback? onTap;
  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final content = Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: scheme.onSurfaceVariant.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 18, color: scheme.onSurfaceVariant),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label,
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: scheme.onSurface)),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: scheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
    if (onTap == null) return content;
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: content,
      ),
    );
  }
}

// ── Easter egg ──────────────────────────────────────────────

class _AutorEasterEggDialog extends StatefulWidget {
  const _AutorEasterEggDialog();

  @override
  State<_AutorEasterEggDialog> createState() => _AutorEasterEggDialogState();
}

class _AutorEasterEggDialogState extends State<_AutorEasterEggDialog>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _scale;
  late final Animation<double> _glow;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    )..forward();
    _scale = CurvedAnimation(parent: _ctrl, curve: Curves.easeOutBack);
    _glow = CurvedAnimation(parent: _ctrl, curve: Curves.easeIn);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final brand = context.brand;
    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      insetPadding: const EdgeInsets.symmetric(horizontal: 28),
      child: ScaleTransition(
        scale: Tween<double>(begin: 0.6, end: 1.0).animate(_scale),
        child: AnimatedBuilder(
          animation: _glow,
          builder: (_, child) => Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: brand.success.withValues(alpha: 0.4 * _glow.value),
                  blurRadius: 60,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: child,
          ),
          child: Container(
            padding: const EdgeInsets.fromLTRB(28, 32, 28, 24),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  scheme.surfaceContainerHigh,
                  scheme.surfaceContainer,
                ],
              ),
              border: Border.all(
                color: brand.success.withValues(alpha: 0.4),
                width: 1.5,
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [brand.success, scheme.primary],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: brand.success.withValues(alpha: 0.5),
                        blurRadius: 24,
                        spreadRadius: -2,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.code_rounded,
                    color: Colors.white,
                    size: 36,
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  'feito com ♥ por',
                  style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 1.8,
                    fontWeight: FontWeight.w600,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 6),
                ShaderMask(
                  shaderCallback: (rect) => LinearGradient(
                    colors: [brand.success, scheme.primary, brand.info],
                  ).createShader(rect),
                  child: const Text(
                    'Robert Albino',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.5,
                      height: 1.1,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'autor do BlaBla Técnico',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: brand.success.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: brand.success.withValues(alpha: 0.30),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.bolt_rounded,
                          size: 14, color: brand.success),
                      const SizedBox(width: 6),
                      Text(
                        'v0.1.0 · build emerald',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: brand.success,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  style: TextButton.styleFrom(
                    foregroundColor: scheme.onSurfaceVariant,
                    textStyle: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  child: const Text('fechar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Mudar senha sheet ───────────────────────────────────────

class _MudarSenhaSheet extends ConsumerStatefulWidget {
  const _MudarSenhaSheet();
  @override
  ConsumerState<_MudarSenhaSheet> createState() => _MudarSenhaSheetState();
}

class _MudarSenhaSheetState extends ConsumerState<_MudarSenhaSheet> {
  final _atual = TextEditingController();
  final _nova = TextEditingController();
  final _confirma = TextEditingController();
  bool _show = false;
  bool _sending = false;
  String? _erro;

  @override
  void dispose() {
    _atual.dispose();
    _nova.dispose();
    _confirma.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final a = _atual.text;
    final n = _nova.text;
    final c = _confirma.text;
    if (n.length < 8) {
      setState(() => _erro = 'Nova senha deve ter pelo menos 8 caracteres.');
      return;
    }
    if (n != c) {
      setState(() => _erro = 'Confirmação não bate com a nova senha.');
      return;
    }
    if (n == a) {
      setState(() => _erro = 'Nova senha deve ser diferente da atual.');
      return;
    }
    setState(() {
      _sending = true;
      _erro = null;
    });
    try {
      await ref
          .read(perfilActionsProvider)
          .mudarSenha(atual: a, nova: n);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Senha alterada com sucesso.')),
        );
      }
    } on DioException catch (e) {
      final msg = e.response?.statusCode == 401
          ? 'Senha atual incorreta.'
          : (e.response?.data is Map
                  ? (e.response!.data as Map)['detail']?.toString() ?? e.message
                  : e.message) ??
              'Erro ao mudar senha.';
      setState(() => _erro = msg);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: EdgeInsets.only(
        bottom: mq.viewInsets.bottom + 16,
        left: 16,
        right: 16,
        top: 16,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: scheme.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text('Mudar senha',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            TextField(
              controller: _atual,
              obscureText: !_show,
              decoration: const InputDecoration(
                labelText: 'Senha atual',
                prefixIcon: Icon(Icons.lock_outline),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _nova,
              obscureText: !_show,
              decoration: InputDecoration(
                labelText: 'Nova senha',
                helperText: 'Pelo menos 8 caracteres',
                prefixIcon: const Icon(Icons.lock_reset),
                suffixIcon: IconButton(
                  icon: Icon(_show ? Icons.visibility_off : Icons.visibility),
                  tooltip: _show ? 'Ocultar' : 'Mostrar',
                  onPressed: () => setState(() => _show = !_show),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _confirma,
              obscureText: !_show,
              decoration: const InputDecoration(
                labelText: 'Confirmar nova senha',
                prefixIcon: Icon(Icons.lock_reset),
              ),
            ),
            if (_erro != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: scheme.errorContainer.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline,
                        size: 18, color: scheme.error),
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
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _sending ? null : _submit,
              child: _sending
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Salvar'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Error/loading wrappers ───────────────────────────────────

class _ErroView extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _ErroView({required this.e, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final panel = isOfflineException(e)
        ? AppStatePanel.offline(
            title: 'Sem conexão para atualizar seu perfil',
            message:
                'Sem rede e sem snapshot local. Tente novamente quando o sinal estabilizar.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          )
        : AppStatePanel.error(
            title: 'Não foi possível carregar seu perfil',
            message: 'Revise a conexão e tente novamente em instantes.',
            actionLabel: 'Tentar novamente',
            onAction: onRetry,
          );
    return _StateBody(child: panel);
  }
}

class _StateBody extends StatelessWidget {
  final Widget child;
  const _StateBody({required this.child});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: child,
        ),
      ),
    );
  }
}
