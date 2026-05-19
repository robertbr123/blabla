import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_client.dart';
import '../../core/location/location_service.dart';
import '../../core/sync/outbox_repo.dart';
import '../../core/sync/sync_service.dart';
import 'os_data.dart';

class OsDetailScreen extends ConsumerWidget {
  final String id;
  const OsDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(osDetailProvider(id));
    return Scaffold(
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
        error: (e, _) => _Erro(e: e, onRetry: () => ref.invalidate(osDetailProvider(id))),
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
      padding: const EdgeInsets.all(12),
      children: [
        pendingAsync.when(
          data: (n) => n > 0
              ? Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: Colors.orange.withValues(alpha: 0.35),
                    ),
                  ),
                  child: Row(children: [
                    const Icon(Icons.cloud_upload,
                        size: 18, color: Color(0xFFd97706)),
                    const SizedBox(width: 6),
                    Text('$n item(ns) aguardando upload',
                        style: const TextStyle(
                          color: Color(0xFFb45309),
                          fontWeight: FontWeight.w600,
                        )),
                  ]),
                )
              : const SizedBox.shrink(),
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
        _Header(os: os),
        const SizedBox(height: 12),
        _Secao(
          icone: Icons.place_outlined,
          titulo: 'Endereço',
          conteudo: os['endereco']?.toString() ?? '—',
        ),
        _Secao(
          icone: Icons.report_problem_outlined,
          titulo: 'Problema relatado',
          conteudo: os['problema']?.toString() ?? '—',
        ),
        if (os['plano'] != null ||
            os['pppoe_login'] != null ||
            os['pppoe_senha'] != null)
          _PppoeCard(
            plano: os['plano'] as String?,
            login: os['pppoe_login'] as String?,
            senha: os['pppoe_senha'] as String?,
          ),
        const SizedBox(height: 24),
        if (podeIniciar)
          FilledButton.icon(
            icon: const Icon(Icons.play_arrow),
            label: const Text('Iniciar visita (com GPS)'),
            onPressed: () => _iniciar(context, ref),
          ),
        if (podeConcluir) ...[
          FilledButton.tonalIcon(
            icon: const Icon(Icons.photo_camera),
            label: const Text('Tirar foto'),
            onPressed: () => _tirarFoto(context, ref),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            icon: const Icon(Icons.check),
            label: const Text('Concluir OS'),
            onPressed: () => _abrirConcluirSheet(context, ref),
          ),
        ],
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
        await svc.enqueue(
          osId: osId,
          kind: OutboxKind.iniciar,
          payload: body,
        );
        _showSnack(context, 'Sem conexão — enfileirado pra envio depois.');
      }
    } catch (e) {
      // Falha online → cai pra fila pra retry
      await svc.enqueue(osId: osId, kind: OutboxKind.iniciar, payload: body);
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
      builder: (_) => _ConcluirSheet(osId: osId, onDone: () {
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
      if (online) {
        try {
          await ref.read(apiClientProvider).post(
                '/api/v1/tecnico/me/os/${widget.osId}/concluir',
                data: body,
              );
        } catch (_) {
          await svc.enqueue(
            osId: widget.osId,
            kind: OutboxKind.concluir,
            payload: body,
          );
        }
      } else {
        await svc.enqueue(
          osId: widget.osId,
          kind: OutboxKind.concluir,
          payload: body,
        );
      }
      widget.onDone();
      if (mounted) {
        Navigator.of(context).pop();
        _Body._showSnack(context, 'OS concluída.');
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

class _Header extends StatelessWidget {
  final Map<String, dynamic> os;
  const _Header({required this.os});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final status = (os['status'] ?? '') as String;
    final c = _statusInfo(status);
    final nome = (os['nome_cliente'] as String?) ?? 'Cliente —';
    final codigo = (os['codigo'] ?? '') as String;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            c.color.withValues(alpha: 0.12),
            c.color.withValues(alpha: 0.04),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                codigo,
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: c.color.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: c.color.withValues(alpha: 0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(c.icon, size: 13, color: c.color),
                    const SizedBox(width: 5),
                    Text(
                      c.label,
                      style: TextStyle(
                        color: c.color,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            nome,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: scheme.onSurface,
              height: 1.15,
            ),
          ),
          const SizedBox(height: 4),
          if (os['agendamento_at'] != null)
            Row(
              children: [
                Icon(Icons.event,
                    size: 14, color: scheme.onSurfaceVariant),
                const SizedBox(width: 5),
                Text(
                  os['agendamento_at'].toString().substring(0, 16).replaceAll('T', ' às '),
                  style: TextStyle(
                    fontSize: 12,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  static ({String label, Color color, IconData icon}) _statusInfo(String s) {
    switch (s) {
      case 'pendente':
        return (label: 'Pendente', color: const Color(0xFFf59e0b), icon: Icons.hourglass_top);
      case 'em_andamento':
        return (label: 'Em andamento', color: const Color(0xFF2563eb), icon: Icons.directions_run);
      case 'concluida':
        return (label: 'Concluída', color: const Color(0xFF16a34a), icon: Icons.check_circle);
      case 'cancelada':
        return (label: 'Cancelada', color: const Color(0xFF6b7280), icon: Icons.cancel);
      default:
        return (label: s, color: const Color(0xFF6b7280), icon: Icons.help_outline);
    }
  }
}

class _Secao extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final String conteudo;
  const _Secao({
    required this.icone,
    required this.titulo,
    required this.conteudo,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icone, size: 16, color: scheme.onSurfaceVariant),
                const SizedBox(width: 6),
                Text(
                  titulo.toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 0.5,
                    fontWeight: FontWeight.w700,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              conteudo,
              style: const TextStyle(fontSize: 14.5, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }
}

class _PppoeCard extends StatelessWidget {
  final String? plano;
  final String? login;
  final String? senha;
  const _PppoeCard({this.plano, this.login, this.senha});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.router, size: 16, color: scheme.onSurfaceVariant),
                const SizedBox(width: 6),
                Text(
                  'CONEXÃO',
                  style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 0.5,
                    fontWeight: FontWeight.w700,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (plano != null) _kv(context, 'Plano', plano!),
            if (login != null) _kv(context, 'Login', login!, mono: true),
            if (senha != null) _kv(context, 'Senha', senha!, mono: true),
          ],
        ),
      ),
    );
  }

  Widget _kv(BuildContext context, String k, String v, {bool mono = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 70,
            child: Text(
              k,
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              v,
              style: TextStyle(
                fontSize: 14,
                fontFamily: mono ? 'monospace' : null,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
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

