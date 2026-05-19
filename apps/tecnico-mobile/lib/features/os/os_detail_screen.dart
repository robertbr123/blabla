import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_client.dart';
import '../../core/location/location_service.dart';
import '../../core/sync/outbox_repo.dart';
import '../../core/sync/sync_service.dart';

final _osDetailProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, id) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/tecnico/me/os/$id');
  return (r.data as Map<String, dynamic>);
});

class OsDetailScreen extends ConsumerWidget {
  final String id;
  const OsDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_osDetailProvider(id));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalhe da OS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(_osDetailProvider(id)),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _Erro(e: e, onRetry: () => ref.invalidate(_osDetailProvider(id))),
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
      padding: const EdgeInsets.all(16),
      children: [
        // Badge pendentes na fila
        pendingAsync.when(
          data: (n) => n > 0
              ? Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(children: [
                    const Icon(Icons.cloud_upload, size: 18, color: Colors.orange),
                    const SizedBox(width: 6),
                    Text('$n item(ns) aguardando upload',
                        style: const TextStyle(color: Colors.orange)),
                  ]),
                )
              : const SizedBox.shrink(),
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
        _Linha('Código', os['codigo']?.toString() ?? '—'),
        _Linha('Status', status),
        _Linha('Cliente', os['nome_cliente']?.toString() ?? '—'),
        _Linha('Problema', os['problema']?.toString() ?? '—'),
        _Linha('Endereço', os['endereco']?.toString() ?? '—'),
        if (os['plano'] != null) _Linha('Plano', os['plano'].toString()),
        if (os['pppoe_login'] != null)
          _Linha('PPPoE login', os['pppoe_login'].toString()),
        if (os['pppoe_senha'] != null)
          _Linha('PPPoE senha', os['pppoe_senha'].toString()),
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
        ref.invalidate(_osDetailProvider(osId));
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
        ref.invalidate(_osDetailProvider(osId));
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

class _Linha extends StatelessWidget {
  final String label;
  final String value;
  const _Linha(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 2),
          Text(value, style: Theme.of(context).textTheme.bodyMedium),
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

