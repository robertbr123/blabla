import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/location/location_service.dart';
import '../../core/sync/outbox_repo.dart';
import '../../core/sync/sync_service.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_status_chip.dart';
import '../../core/ui/app_surfaces.dart';
import 'os_data.dart';
import 'widgets/cliente_avatar.dart';

class OsDetailScreen extends ConsumerWidget {
  final String id;
  const OsDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(osDetailProvider(id));
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Detalhe da OS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(osDetailProvider(id)),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            _Erro(e: e, onRetry: () => ref.invalidate(osDetailProvider(id))),
        data: (os) => _Body(osId: id, os: os),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  final String osId;
  final Map<String, dynamic> os;
  const _Body({required this.osId, required this.os});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pendingAsync = ref.watch(pendingCountProvider);
    final status = os['status']?.toString() ?? '';
    final isPendente = status == 'pendente';
    final isEmAndamento = status == 'em_andamento';
    final podeConcluir = isEmAndamento;
    final podeIniciar = isPendente;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        pendingAsync.when(
          data: (n) => n > 0
              ? Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _PendingSyncBanner(count: n),
                )
              : const SizedBox.shrink(),
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
        _StatusSection(os: os),
        const SizedBox(height: 12),
        _ContextSection(
          endereco: os['endereco']?.toString() ?? '—',
          problema: os['problema']?.toString() ?? '—',
          plano: os['plano'] as String?,
          login: os['pppoe_login'] as String?,
          senha: os['pppoe_senha'] as String?,
        ),
        const SizedBox(height: 12),
        _ActionsSection(
          canStart: podeIniciar,
          canConclude: podeConcluir,
          onStart: () => _iniciar(context, ref),
          onConclude: () => _abrirConcluirSheet(context, ref),
        ),
        const SizedBox(height: 12),
        _PhotosSection(
          canTakePhoto: podeConcluir,
          onTakePhoto: () => _tirarFoto(context, ref),
        ),
      ],
    );
  }

  Future<void> _iniciar(BuildContext context, WidgetRef ref) async {
    _showSnack(context, 'Capturando GPS…');
    final loc = await LocationService().capture();
    final body = {
      if (loc != null) 'lat': loc.lat,
      if (loc != null) 'lng': loc.lng,
    };
    final online = await _isOnline();
    final svc = ref.read(syncServiceProvider);
    try {
      if (online) {
        await ref.read(apiClientProvider).post(
              '/api/v1/tecnico/me/os/$osId/iniciar',
              data: body,
            );
        ref.invalidate(osDetailProvider(osId));
        _showSnack(context, 'OS iniciada ✅');
      } else {
        await ref.read(osLocalRepoProvider).markStartedOptimistic(osId);
        await svc.enqueue(
          osId: osId,
          kind: OutboxKind.iniciar,
          payload: body,
        );
        ref.invalidate(osDetailProvider(osId));
        _showSnack(context, 'Sem conexão — enfileirado pra envio depois.');
      }
    } catch (e) {
      // Falha online → cai pra fila pra retry
      await ref.read(osLocalRepoProvider).markStartedOptimistic(osId);
      await svc.enqueue(osId: osId, kind: OutboxKind.iniciar, payload: body);
      ref.invalidate(osDetailProvider(osId));
      _showSnack(context, 'Falha online: enfileirado pra retry. ($e)');
    }
  }

  Future<void> _tirarFoto(BuildContext context, WidgetRef ref) async {
    final picker = ImagePicker();
    final x = await picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
      maxWidth: 1920,
    );
    if (x == null) return;
    final svc = ref.read(syncServiceProvider);
    await svc.enqueue(
      osId: osId,
      kind: OutboxKind.foto,
      payload: const {},
      filePath: x.path,
    );
    _showSnack(context, 'Foto enfileirada (sobe assim que possível).');
    unawaited(svc.flush());
  }

  Future<void> _abrirConcluirSheet(BuildContext context, WidgetRef ref) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ConcluirSheet(
          osId: osId,
          onDone: () {
            ref.invalidate(osDetailProvider(osId));
          }),
    );
  }

  static Future<bool> _isOnline() async {
    final r = await Connectivity().checkConnectivity();
    return r.any((c) => c != ConnectivityResult.none);
  }

  static void _showSnack(BuildContext ctx, String msg) {
    if (!ctx.mounted) return;
    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(msg)));
  }
}

class _ConcluirSheet extends ConsumerStatefulWidget {
  final String osId;
  final VoidCallback onDone;
  const _ConcluirSheet({required this.osId, required this.onDone});

  @override
  ConsumerState<_ConcluirSheet> createState() => _ConcluirSheetState();
}

class _ConcluirSheetState extends ConsumerState<_ConcluirSheet> {
  final _relatorio = TextEditingController();
  final _materiais = TextEditingController();
  int? _csat;
  bool _houveVisita = true;
  bool _enviando = false;

  @override
  void dispose() {
    _relatorio.dispose();
    _materiais.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    setState(() => _enviando = true);
    try {
      final loc = await LocationService().capture();
      final body = {
        if (_csat != null) 'csat': _csat,
        if (_relatorio.text.trim().isNotEmpty)
          'relatorio': _relatorio.text.trim(),
        if (_materiais.text.trim().isNotEmpty)
          'materiais': _materiais.text.trim(),
        'houve_visita': _houveVisita,
        if (loc != null) 'lat': loc.lat,
        if (loc != null) 'lng': loc.lng,
      };
      final online = await _Body._isOnline();
      final svc = ref.read(syncServiceProvider);
      var completionMessage = 'OS concluída.';
      if (online) {
        try {
          await ref.read(apiClientProvider).post(
                '/api/v1/tecnico/me/os/${widget.osId}/concluir',
                data: body,
              );
        } catch (_) {
          await ref
              .read(osLocalRepoProvider)
              .markConcludedOptimistic(widget.osId, body);
          await svc.enqueue(
            osId: widget.osId,
            kind: OutboxKind.concluir,
            payload: body,
          );
          completionMessage = 'Falha online — conclusão enfileirada pra retry.';
        }
      } else {
        await ref
            .read(osLocalRepoProvider)
            .markConcludedOptimistic(widget.osId, body);
        await svc.enqueue(
          osId: widget.osId,
          kind: OutboxKind.concluir,
          payload: body,
        );
        completionMessage =
            'Sem conexão — conclusão enfileirada pra envio depois.';
      }
      widget.onDone();
      if (mounted) {
        Navigator.of(context).pop();
        _Body._showSnack(context, completionMessage);
      }
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
            const Text('Concluir OS',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: _relatorio,
              decoration: const InputDecoration(
                labelText: 'Relatório do atendimento',
                border: OutlineInputBorder(),
              ),
              maxLines: 4,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _materiais,
              decoration: const InputDecoration(
                labelText: 'Materiais utilizados',
                border: OutlineInputBorder(),
                helperText: 'Ex: 50m cabo, 2 conectores',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              title: const Text('Houve visita ao local'),
              value: _houveVisita,
              onChanged: (v) => setState(() => _houveVisita = v),
            ),
            const SizedBox(height: 8),
            const Text('CSAT (opcional — se cliente avaliou no local)'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [1, 2, 3, 4, 5]
                  .map((n) => ChoiceChip(
                        label: Text('$n'),
                        selected: _csat == n,
                        onSelected: (s) => setState(() => _csat = s ? n : null),
                      ))
                  .toList(),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _enviando ? null : _enviar,
              child: _enviando
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Concluir'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PendingSyncBanner extends StatelessWidget {
  final int count;

  const _PendingSyncBanner({required this.count});

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFFd97706);

    return AppSurfaceCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.cloud_upload_rounded,
              size: 18,
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '$count item(ns) aguardando upload',
              style: const TextStyle(
                color: Color(0xFFb45309),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusSection extends StatelessWidget {
  final Map<String, dynamic> os;

  const _StatusSection({required this.os});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final statusInfo = _StatusInfo.of((os['status'] ?? '') as String);
    final nome = (os['nome_cliente'] as String?) ?? 'Cliente —';
    final codigo = (os['codigo'] ?? '') as String;
    final agendamento = _parseDate(os['agendamento_at']?.toString());

    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppSectionHeader(
            title: 'Status da OS',
            subtitle: 'Panorama rápido da visita e do agendamento.',
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClienteAvatar(nome: nome, size: 56),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      nome,
                      style: TextStyle(
                        color: scheme.onSurface,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        height: 1.1,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      codigo,
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: scheme.onSurfaceVariant,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              AppStatusChip(
                label: statusInfo.label,
                tone: statusInfo.tone,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _DetailMetaPill(
                icon: statusInfo.icon,
                label: statusInfo.label,
                color: statusInfo.color,
              ),
              if (agendamento != null)
                _DetailMetaPill(
                  icon: Icons.event_rounded,
                  label: DateFormat("dd/MM 'às' HH:mm")
                      .format(agendamento.toLocal()),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ContextSection extends StatelessWidget {
  final String endereco;
  final String problema;
  final String? plano;
  final String? login;
  final String? senha;

  const _ContextSection({
    required this.endereco,
    required this.problema,
    required this.plano,
    required this.login,
    required this.senha,
  });

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppSectionHeader(
            title: 'Contexto',
            subtitle: 'Dados do local e do atendimento reportado.',
          ),
          const SizedBox(height: 16),
          _DetailField(
            icon: Icons.place_outlined,
            title: 'Endereço',
            content: endereco,
          ),
          const SizedBox(height: 16),
          _DetailField(
            icon: Icons.report_problem_outlined,
            title: 'Problema relatado',
            content: problema,
          ),
          if (plano != null || login != null || senha != null) ...[
            const SizedBox(height: 18),
            const Divider(height: 1),
            const SizedBox(height: 18),
            _ConnectionBlock(plano: plano, login: login, senha: senha),
          ],
        ],
      ),
    );
  }
}

class _ActionsSection extends StatelessWidget {
  final bool canStart;
  final bool canConclude;
  final VoidCallback onStart;
  final VoidCallback onConclude;

  const _ActionsSection({
    required this.canStart,
    required this.canConclude,
    required this.onStart,
    required this.onConclude,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppSectionHeader(
            title: 'Ações',
            subtitle: canStart || canConclude
                ? 'Próximo passo operacional disponível para esta OS.'
                : 'Esta OS não tem ações operacionais pendentes.',
          ),
          const SizedBox(height: 16),
          if (canStart)
            FilledButton.icon(
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text('Iniciar visita (com GPS)'),
              onPressed: onStart,
            ),
          if (canConclude)
            FilledButton.icon(
              icon: const Icon(Icons.check_rounded),
              label: const Text('Concluir OS'),
              onPressed: onConclude,
            ),
          if (!canStart && !canConclude)
            Text(
              'O atendimento já foi encerrado ou não exige uma próxima ação.',
              style: TextStyle(
                color: scheme.onSurfaceVariant,
                height: 1.4,
              ),
            ),
        ],
      ),
    );
  }
}

class _PhotosSection extends StatelessWidget {
  final bool canTakePhoto;
  final VoidCallback onTakePhoto;

  const _PhotosSection({
    required this.canTakePhoto,
    required this.onTakePhoto,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppSectionHeader(
            title: 'Fotos',
            subtitle: canTakePhoto
                ? 'Registre evidências do atendimento antes da conclusão.'
                : 'As fotos ficam disponíveis quando a visita está em andamento.',
          ),
          const SizedBox(height: 16),
          if (canTakePhoto)
            FilledButton.tonalIcon(
              icon: const Icon(Icons.photo_camera_rounded),
              label: const Text('Tirar foto'),
              onPressed: onTakePhoto,
            )
          else
            Text(
              'Inicie a visita para liberar o registro de fotos de campo.',
              style: TextStyle(
                color: scheme.onSurfaceVariant,
                height: 1.4,
              ),
            ),
        ],
      ),
    );
  }
}

class _DetailField extends StatelessWidget {
  final IconData icon;
  final String title;
  final String content;

  const _DetailField({
    required this.icon,
    required this.title,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: scheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, size: 18, color: scheme.onSurfaceVariant),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: scheme.onSurfaceVariant,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                content,
                style: TextStyle(
                  color: scheme.onSurface,
                  fontSize: 15,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ConnectionBlock extends StatelessWidget {
  final String? plano;
  final String? login;
  final String? senha;

  const _ConnectionBlock({
    required this.plano,
    required this.login,
    required this.senha,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.router_rounded,
                size: 16, color: scheme.onSurfaceVariant),
            const SizedBox(width: 8),
            Text(
              'Conexão',
              style: TextStyle(
                color: scheme.onSurface,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (plano != null) _ConnectionRow(label: 'Plano', value: plano!),
        if (login != null)
          _ConnectionRow(label: 'Login', value: login!, mono: true),
        if (senha != null)
          _ConnectionRow(label: 'Senha', value: senha!, mono: true),
      ],
    );
  }
}

class _ConnectionRow extends StatelessWidget {
  final String label;
  final String value;
  final bool mono;

  const _ConnectionRow({
    required this.label,
    required this.value,
    this.mono = false,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: scheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: TextStyle(
                fontSize: 14,
                fontFamily: mono ? 'monospace' : null,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailMetaPill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;

  const _DetailMetaPill({
    required this.icon,
    required this.label,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final resolvedColor = color ?? scheme.onSurfaceVariant;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: resolvedColor.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: resolvedColor),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: resolvedColor,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusInfo {
  final String label;
  final Color color;
  final IconData icon;
  final AppStatusTone tone;

  const _StatusInfo(this.label, this.color, this.icon, this.tone);

  static _StatusInfo of(String status) {
    switch (status) {
      case 'pendente':
        return const _StatusInfo(
          'Pendente',
          Color(0xFFf59e0b),
          Icons.hourglass_top_rounded,
          AppStatusTone.warning,
        );
      case 'em_andamento':
        return const _StatusInfo(
          'Em andamento',
          Color(0xFF2563eb),
          Icons.directions_run_rounded,
          AppStatusTone.info,
        );
      case 'concluida':
        return const _StatusInfo(
          'Concluída',
          Color(0xFF16a34a),
          Icons.check_circle_rounded,
          AppStatusTone.success,
        );
      case 'cancelada':
        return const _StatusInfo(
          'Cancelada',
          Color(0xFF6b7280),
          Icons.cancel_rounded,
          AppStatusTone.neutral,
        );
      default:
        return _StatusInfo(
          status,
          const Color(0xFF6b7280),
          Icons.help_outline_rounded,
          AppStatusTone.neutral,
        );
    }
  }
}

DateTime? _parseDate(String? value) {
  if (value == null || value.isEmpty) {
    return null;
  }
  return DateTime.tryParse(value);
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
