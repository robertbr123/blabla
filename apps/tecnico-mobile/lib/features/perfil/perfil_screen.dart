import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/auth/auth_repository.dart';
import '../../core/auth/session_cleanup.dart';
import '../../core/push/fcm_service.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_status_chip.dart';
import '../../core/ui/app_surfaces.dart';
import '../os/widgets/cliente_avatar.dart';
import 'perfil_data.dart';

class PerfilScreen extends ConsumerWidget {
  const PerfilScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(perfilProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Meu perfil'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(perfilProvider),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _Erro(
          e: e,
          onRetry: () => ref.invalidate(perfilProvider),
        ),
        data: (p) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(perfilProvider),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            children: [
              AppSurfaceCard(child: _HeaderCard(perfil: p)),
              const SizedBox(height: 12),
              AppSurfaceCard(child: _Estatisticas(stats: p.estatisticas)),
              const SizedBox(height: 12),
              _Secao(
                titulo: 'Conta',
                subtitulo:
                    'Atualize credenciais e encerre sua sessão com segurança.',
                children: [
                  _ItemAcao(
                    icone: Icons.lock_outline,
                    titulo: 'Mudar senha',
                    onTap: () => _abrirMudarSenha(context, ref),
                  ),
                  _ItemAcao(
                    icone: Icons.logout,
                    titulo: 'Sair',
                    destrutivo: true,
                    onTap: () => _sair(context, ref),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const _Secao(
                titulo: 'Sobre',
                subtitulo:
                    'Informações da versão e da operação vinculada a este app.',
                children: [
                  _ItemInfo(
                    icone: Icons.smartphone,
                    label: 'Versão',
                    value: '0.1.0',
                  ),
                  _ItemInfo(
                    icone: Icons.business,
                    label: 'Empresa',
                    value: 'Linket',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _abrirMudarSenha(BuildContext context, WidgetRef ref) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _MudarSenhaSheet(),
    );
  }

  Future<void> _sair(BuildContext context, WidgetRef ref) async {
    final confirma = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sair?'),
        content:
            const Text('Você terá que fazer login de novo pra acessar o app.'),
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

class _HeaderCard extends ConsumerStatefulWidget {
  final Perfil perfil;
  const _HeaderCard({required this.perfil});

  @override
  ConsumerState<_HeaderCard> createState() => _HeaderCardState();
}

class _HeaderCardState extends ConsumerState<_HeaderCard> {
  bool _uploading = false;

  Future<void> _trocarFoto() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera),
              title: const Text('Tirar foto'),
              onTap: () => Navigator.of(context).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Escolher da galeria'),
              onTap: () => Navigator.of(context).pop(ImageSource.gallery),
            ),
            if (widget.perfil.hasFoto)
              ListTile(
                leading: Icon(Icons.delete_outline,
                    color: Theme.of(context).colorScheme.error),
                title: Text(
                  'Remover foto atual',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
                onTap: () => Navigator.of(context).pop(null),
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (!mounted) return;

    if (source == null) {
      // Remover
      setState(() => _uploading = true);
      try {
        await ref.read(perfilActionsProvider).removerFoto();
        ref.invalidate(perfilProvider);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Foto removida.')),
          );
        }
      } finally {
        if (mounted) setState(() => _uploading = false);
      }
      return;
    }

    final picker = ImagePicker();
    final x = await picker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 1200,
    );
    if (x == null || !mounted) return;
    setState(() => _uploading = true);
    try {
      await ref.read(perfilActionsProvider).uploadFoto(x.path);
      ref.invalidate(perfilProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Foto atualizada.')),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Falhou: ${e.message ?? e.type.name}')),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final p = widget.perfil;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionHeader(
          title: 'Perfil em campo',
          subtitle: 'Foto, contato e status operacional da sua sessão atual.',
        ),
        const SizedBox(height: 16),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: scheme.brightness == Brightness.dark
                  ? const [Color(0xFF1e293b), Color(0xFF0f172a)]
                  : const [Color(0xFFEAF0F6), Color(0xFFF8F5EE)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(22),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Stack(
                children: [
                  GestureDetector(
                    onTap: _uploading ? null : _trocarFoto,
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
                      onTap: _uploading ? null : _trocarFoto,
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
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      p.nome,
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: scheme.onSurface,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 6),
                    _ContatoLinha(
                      icon: Icons.email_outlined,
                      value: p.email,
                    ),
                    if (p.contatoWhatsapp != null) ...[
                      const SizedBox(height: 4),
                      _ContatoLinha(
                        icon: Icons.phone_iphone,
                        value: p.contatoWhatsapp!,
                      ),
                    ],
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        AppStatusChip(
                          label: p.availabilityLabel,
                          tone: p.ativo
                              ? AppStatusTone.success
                              : AppStatusTone.warning,
                        ),
                        AppStatusChip(
                          label: p.roleLabel,
                          tone: AppStatusTone.info,
                        ),
                        if (p.hasLastGpsSnapshot)
                          const AppStatusChip(
                            label: 'GPS recente',
                            tone: AppStatusTone.neutral,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Estatisticas extends StatelessWidget {
  final PerfilEstatisticas stats;
  const _Estatisticas({required this.stats});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionHeader(
          title: 'Sua atividade recente',
          subtitle:
              'Acompanhe a fila atual, o andamento das ordens e a percepção do atendimento.',
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            _StatCard(
              label: 'Pendentes',
              value: '${stats.osPendentes}',
              color: const Color(0xFFf59e0b),
              icon: Icons.hourglass_top,
            ),
            const SizedBox(width: 10),
            _StatCard(
              label: 'Em andamento',
              value: '${stats.osEmAndamento}',
              color: scheme.primary,
              icon: Icons.directions_run,
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _StatCard(
              label: 'Concluídas (mês)',
              value: '${stats.osConcluidasMes}',
              color: const Color(0xFF16a34a),
              icon: Icons.check_circle,
            ),
            const SizedBox(width: 10),
            _StatCard(
              label: 'CSAT médio',
              value: stats.csatAvgMes != null
                  ? stats.csatAvgMes!.toStringAsFixed(1)
                  : '—',
              color: const Color(0xFF8b5cf6),
              icon: Icons.star,
            ),
          ],
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  final IconData icon;
  const _StatCard({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 18),
                const Spacer(),
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: scheme.onSurface,
                    height: 1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 11.5,
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

class _Secao extends StatelessWidget {
  final String titulo;
  final String? subtitulo;
  final List<Widget> children;
  const _Secao({
    required this.titulo,
    this.subtitulo,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppSectionHeader(
            title: titulo,
            subtitle: subtitulo,
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0)
              Divider(
                height: 1,
                color: scheme.outlineVariant.withValues(alpha: 0.6),
              ),
            children[i],
          ],
        ],
      ),
    );
  }
}

class _ItemAcao extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final VoidCallback onTap;
  final bool destrutivo;
  const _ItemAcao({
    required this.icone,
    required this.titulo,
    required this.onTap,
    this.destrutivo = false,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = destrutivo ? scheme.error : scheme.onSurface;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: _LeadingIcon(icon: icone, color: color),
      title: Text(
        titulo,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
      trailing: Icon(Icons.chevron_right, color: scheme.onSurfaceVariant),
      onTap: onTap,
    );
  }
}

class _ItemInfo extends StatelessWidget {
  final IconData icone;
  final String label;
  final String value;
  const _ItemInfo({
    required this.icone,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: _LeadingIcon(
        icon: icone,
        color: scheme.onSurfaceVariant,
      ),
      title: Text(
        label,
        style: TextStyle(
          color: scheme.onSurface,
          fontWeight: FontWeight.w600,
        ),
      ),
      trailing: Text(
        value,
        style: TextStyle(
          fontWeight: FontWeight.w600,
          color: scheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _ContatoLinha extends StatelessWidget {
  final IconData icon;
  final String value;
  const _ContatoLinha({
    required this.icon,
    required this.value,
  });

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
            style: TextStyle(
              fontSize: 12,
              color: scheme.onSurfaceVariant,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _LeadingIcon extends StatelessWidget {
  final IconData icon;
  final Color color;
  const _LeadingIcon({
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
      ),
      alignment: Alignment.center,
      child: Icon(icon, color: color, size: 20),
    );
  }
}

class _MudarSenhaSheet extends ConsumerStatefulWidget {
  const _MudarSenhaSheet();
  @override
  ConsumerState<_MudarSenhaSheet> createState() => _MudarSenhaSheetState();
}

class _MudarSenhaSheetState extends ConsumerState<_MudarSenhaSheet> {
  final _atual = TextEditingController();
  final _nova = TextEditingController();
  final _confirma = TextEditingController();
  bool _mostrar = false;
  bool _enviando = false;
  String? _erro;

  @override
  void dispose() {
    _atual.dispose();
    _nova.dispose();
    _confirma.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    final atual = _atual.text;
    final nova = _nova.text;
    final conf = _confirma.text;
    if (nova.length < 8) {
      setState(() => _erro = 'Nova senha deve ter pelo menos 8 caracteres.');
      return;
    }
    if (nova != conf) {
      setState(() => _erro = 'Confirmação não bate com a nova senha.');
      return;
    }
    if (nova == atual) {
      setState(() => _erro = 'Nova senha deve ser diferente da atual.');
      return;
    }
    setState(() {
      _enviando = true;
      _erro = null;
    });
    try {
      await ref.read(perfilActionsProvider).mudarSenha(
            atual: atual,
            nova: nova,
          );
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
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
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
                  color: Colors.grey.shade400,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Mudar senha',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _atual,
              obscureText: !_mostrar,
              decoration: const InputDecoration(
                labelText: 'Senha atual',
                prefixIcon: Icon(Icons.lock_outline),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _nova,
              obscureText: !_mostrar,
              decoration: InputDecoration(
                labelText: 'Nova senha',
                helperText: 'Pelo menos 8 caracteres',
                prefixIcon: const Icon(Icons.lock_reset),
                suffixIcon: IconButton(
                  icon:
                      Icon(_mostrar ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _mostrar = !_mostrar),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _confirma,
              obscureText: !_mostrar,
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
                  color: Theme.of(context)
                      .colorScheme
                      .errorContainer
                      .withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline,
                        size: 18, color: Theme.of(context).colorScheme.error),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _erro!,
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _enviando ? null : _enviar,
              child: _enviando
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

class _Erro extends StatelessWidget {
  final Object e;
  final VoidCallback onRetry;
  const _Erro({required this.e, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.error_outline, size: 56),
        const SizedBox(height: 12),
        Text(e.toString(), textAlign: TextAlign.center),
        const SizedBox(height: 12),
        FilledButton(onPressed: onRetry, child: const Text('Tentar de novo')),
      ]),
    );
  }
}
