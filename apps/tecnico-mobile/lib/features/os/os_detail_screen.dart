import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/location/location_service.dart';
import '../../core/sync/outbox_repo.dart';
import '../../core/sync/sync_service.dart';
import '../../core/branding/brand_status_pill.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_surfaces.dart';
import 'os_data.dart';
import 'widgets/cliente_avatar.dart';

Color _corSinal(num? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}

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
    final status = os.readString('status', fallback: '');
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
          endereco: os.readString('endereco'),
          problema: os.readString('problema'),
          plano: os.readOptionalString('plano'),
          login: os.readOptionalString('pppoe_login'),
          senha: os.readOptionalString('pppoe_senha'),
          sinalRx: (os['sinal'] as Map<String, dynamic>?)?['rx_power'] as num?,
          sinalStatus: (os['sinal'] as Map<String, dynamic>?)?['status_gpon'] as String?,
        ),
        if (_visitLocation(os) case final location?) ...[
          const SizedBox(height: 12),
          _LocationSection(location: location),
        ],
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

  _VisitLocation? _visitLocation(Map<String, dynamic> os) {
    final endLat = _readDouble(os['gps_fim_lat']);
    final endLng = _readDouble(os['gps_fim_lng']);
    if (endLat != null && endLng != null) {
      return _VisitLocation(
        lat: endLat,
        lng: endLng,
        label: 'Ponto de conclusão',
      );
    }

    final startLat = _readDouble(os['gps_inicio_lat']);
    final startLng = _readDouble(os['gps_inicio_lng']);
    if (startLat != null && startLng != null) {
      return _VisitLocation(
        lat: startLat,
        lng: startLng,
        label: 'Ponto de início',
      );
    }
    return null;
  }

  double? _readDouble(Object? value) {
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  Future<void> _iniciar(BuildContext context, WidgetRef ref) async {
    // O botão já mostra "Capturando GPS…" enquanto este future resolve.
    final loc = await ref.read(locationServiceProvider).capture();
    final body = {
      if (loc != null) 'lat': loc.lat,
      if (loc != null) 'lng': loc.lng,
    };
    final online = await _isOnline();
    final svc = ref.read(syncServiceProvider);
    try {
      if (online) {
        try {
          await ref.read(apiClientProvider).post(
                '/api/v1/tecnico/me/os/$osId/iniciar',
                data: body,
              );
          await ref.read(osLocalRepoProvider).markStartedOptimistic(osId);
          ref.invalidate(osDetailProvider(osId));
          _showSnack(context, 'OS iniciada ✅');
        } on DioException catch (e) {
          if (isRetryableSyncError(e)) {
            await ref.read(osLocalRepoProvider).markStartedOptimistic(osId);
            await svc.enqueue(
              osId: osId,
              kind: OutboxKind.iniciar,
              payload: body,
            );
            ref.invalidate(osDetailProvider(osId));
            _showSnack(context, 'Falha transitória — enfileirado pra retry.');
            return;
          }
          _showSnack(context, _actionFailureMessage('iniciar', e));
          return;
        }
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
    } catch (_) {
      _showSnack(context, 'Não foi possível iniciar a OS agora.');
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
      final loc = await ref.read(locationServiceProvider).capture();
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
          await ref
              .read(osLocalRepoProvider)
              .markConcludedOptimistic(widget.osId, body);
        } on DioException catch (e) {
          if (isRetryableSyncError(e)) {
            await ref
                .read(osLocalRepoProvider)
                .markConcludedOptimistic(widget.osId, body);
            await svc.enqueue(
              osId: widget.osId,
              kind: OutboxKind.concluir,
              payload: body,
            );
            completionMessage =
                'Falha transitória — conclusão enfileirada pra retry.';
          } else {
            _Body._showSnack(context, _actionFailureMessage('concluir', e));
            return;
          }
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
    } catch (_) {
      if (mounted) {
        _Body._showSnack(context, 'Não foi possível concluir a OS agora.');
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

String _actionFailureMessage(String action, DioException error) {
  final base = action == 'iniciar'
      ? 'Não foi possível iniciar a OS.'
      : 'Não foi possível concluir a OS.';
  final detail = error.response?.data is Map<String, dynamic>
      ? (error.response?.data as Map<String, dynamic>)['detail']?.toString()
      : null;
  if (detail == null || detail.trim().isEmpty) {
    return base;
  }
  return '$base $detail';
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
    final statusInfo = _StatusInfo.of(os.readString('status', fallback: ''));
    final nome = os.readString('nome_cliente');
    final codigo = os.readString('codigo', fallback: '');
    final agendamento = _parseDate(os.readOptionalString('agendamento_at'));

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
              BrandStatusPill(
                label: statusInfo.label,
                icon: statusInfo.icon,
                tone: statusInfo.tone,
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (agendamento != null)
            _DetailMetaPill(
              icon: Icons.event_rounded,
              label:
                  DateFormat("dd/MM 'às' HH:mm").format(agendamento.toLocal()),
            )
          else
            Text(
              'Sem agendamento registrado para esta OS.',
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

class _ContextSection extends StatelessWidget {
  final String endereco;
  final String problema;
  final String? plano;
  final String? login;
  final String? senha;
  final num? sinalRx;
  final String? sinalStatus;

  const _ContextSection({
    required this.endereco,
    required this.problema,
    required this.plano,
    required this.login,
    required this.senha,
    this.sinalRx,
    this.sinalStatus,
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
          if (sinalRx != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(children: [
                Icon(Icons.circle, size: 12, color: _corSinal(sinalRx)),
                const SizedBox(width: 8),
                Text('Sinal: $sinalRx dBm'
                    '${sinalStatus != null ? ' · $sinalStatus' : ''}'),
              ]),
            ),
        ],
      ),
    );
  }
}

class _VisitLocation {
  final double lat;
  final double lng;
  final String label;

  const _VisitLocation({
    required this.lat,
    required this.lng,
    required this.label,
  });
}

class _LocationSection extends StatelessWidget {
  final _VisitLocation location;

  const _LocationSection({required this.location});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final staticMapUri = Uri.https(
      'staticmap.openstreetmap.de',
      '/staticmap.php',
      {
        'center': '${location.lat},${location.lng}',
        'zoom': '15',
        'size': '800x320',
        'markers': '${location.lat},${location.lng},red-pushpin',
      },
    );

    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppSectionHeader(
            title: 'Localização da visita',
            subtitle:
                'Use o ponto salvo pela equipe em campo para identificar onde a OS foi executada.',
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: AspectRatio(
              aspectRatio: 2.1,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  ColoredBox(color: scheme.surfaceContainerLow),
                  Image.network(
                    staticMapUri.toString(),
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) =>
                        _MapFallback(location: location),
                    loadingBuilder: (_, child, progress) {
                      if (progress == null) return child;
                      return const Center(
                        child: SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      location.label,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: scheme.onSurface,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${location.lat.toStringAsFixed(6)}, ${location.lng.toStringAsFixed(6)}',
                      style: TextStyle(
                        fontSize: 12,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              FilledButton.tonalIcon(
                onPressed: () => launchUrl(
                  Uri.parse(
                    'https://maps.apple.com/?q=${location.lat},${location.lng}',
                  ),
                  mode: LaunchMode.externalApplication,
                ),
                icon: const Icon(Icons.map_outlined),
                label: const Text('Abrir no Mapas'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MapFallback extends StatelessWidget {
  final _VisitLocation location;

  const _MapFallback({required this.location});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      color: scheme.surfaceContainerLow,
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.location_pin,
            size: 34,
            color: scheme.primary,
          ),
          const SizedBox(height: 10),
          Text(
            'Mapa indisponível neste momento',
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: scheme.onSurface,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${location.lat.toStringAsFixed(6)}, ${location.lng.toStringAsFixed(6)}',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              color: scheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionsSection extends StatefulWidget {
  final bool canStart;
  final bool canConclude;
  final Future<void> Function() onStart;
  final VoidCallback onConclude;

  const _ActionsSection({
    required this.canStart,
    required this.canConclude,
    required this.onStart,
    required this.onConclude,
  });

  @override
  State<_ActionsSection> createState() => _ActionsSectionState();
}

class _ActionsSectionState extends State<_ActionsSection> {
  bool _starting = false;

  Future<void> _handleStart() async {
    if (_starting) return;
    setState(() => _starting = true);
    try {
      await widget.onStart();
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final canStart = widget.canStart;
    final canConclude = widget.canConclude;

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
              icon: _starting
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.play_arrow_rounded),
              label: Text(_starting
                  ? 'Capturando GPS…'
                  : 'Iniciar visita (com GPS)'),
              onPressed: _starting ? null : _handleStart,
            ),
          if (canConclude)
            FilledButton.icon(
              icon: const Icon(Icons.check_rounded),
              label: const Text('Concluir OS'),
              onPressed: widget.onConclude,
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

  const _DetailMetaPill({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final resolvedColor = scheme.onSurfaceVariant;

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
  final IconData icon;
  final BrandTone tone;

  const _StatusInfo(this.label, this.icon, this.tone);

  static _StatusInfo of(String status) {
    switch (status) {
      case 'pendente':
        return const _StatusInfo(
            'Pendente', Icons.hourglass_top_outlined, BrandTone.info);
      case 'em_andamento':
        return const _StatusInfo(
            'Em andamento', Icons.play_circle_outline, BrandTone.warning);
      case 'concluida':
        return const _StatusInfo(
            'Concluída', Icons.check_circle_outline, BrandTone.success);
      case 'cancelada':
        return const _StatusInfo(
            'Cancelada', Icons.cancel_outlined, BrandTone.danger);
      default:
        return _StatusInfo(status, Icons.help_outline, BrandTone.neutral);
    }
  }
}

DateTime? _parseDate(String? value) {
  if (value == null || value.isEmpty) {
    return null;
  }
  return DateTime.tryParse(value);
}

extension on Map<String, dynamic> {
  String readString(String key, {String fallback = '—'}) {
    final value = this[key];
    if (value == null) {
      return fallback;
    }

    final normalized = value.toString().trim();
    return normalized.isEmpty ? fallback : normalized;
  }

  String? readOptionalString(String key) {
    final value = this[key];
    if (value == null) {
      return null;
    }

    final normalized = value.toString().trim();
    return normalized.isEmpty ? null : normalized;
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
