import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/api/api_client.dart';
import '../../../core/auth/auth_storage.dart';
import '../../../core/ui/app_state_panel.dart';
import '../../../core/ui/app_surfaces.dart';
import '../cliente_data.dart';
import '../cliente_form_data.dart';

const _tipos = <({String key, String label, IconData icon, Color color})>[
  (
    key: 'serial',
    label: 'Serial',
    icon: Icons.qr_code_2,
    color: Color(0xFF7c3aed)
  ),
  (
    key: 'instalacao',
    label: 'Instalação',
    icon: Icons.engineering,
    color: Color(0xFF2563eb)
  ),
  (
    key: 'speedtest',
    label: 'Speedtest',
    icon: Icons.speed,
    color: Color(0xFF16a34a)
  ),
  (key: 'outro', label: 'Outro', icon: Icons.photo, color: Color(0xFF6b7280)),
];

({String label, IconData icon, Color color}) _tipoInfo(String key) {
  for (final t in _tipos) {
    if (t.key == key) return (label: t.label, icon: t.icon, color: t.color);
  }
  return (label: key, icon: Icons.photo, color: const Color(0xFF6b7280));
}

class ClienteFotosSection extends ConsumerStatefulWidget {
  final ClienteCampo cliente;
  const ClienteFotosSection({super.key, required this.cliente});

  @override
  ConsumerState<ClienteFotosSection> createState() =>
      _ClienteFotosSectionState();
}

class _ClienteFotosSectionState extends ConsumerState<ClienteFotosSection> {
  bool _uploading = false;

  Future<void> _adicionarFoto() async {
    final escolha =
        await showModalBottomSheet<({ImageSource source, String tipo})?>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _AdicionarFotoSheet(),
    );
    if (escolha == null) return;

    final picker = ImagePicker();
    final x = await picker.pickImage(
      source: escolha.source,
      imageQuality: 85,
      maxWidth: 1920,
    );
    if (x == null || !mounted) return;

    setState(() => _uploading = true);
    try {
      await ref.read(clienteFormActionsProvider).uploadFoto(
            clienteId: widget.cliente.id,
            filePath: x.path,
            tipo: escolha.tipo,
          );
      ref.invalidate(clienteDetailProvider(widget.cliente.id));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Foto enviada.')),
        );
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              extractDioMessage(
                e,
                fallback: 'Não consegui enviar a foto agora.',
              ),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              e.toString().trim().isEmpty
                  ? 'Não consegui enviar a foto agora.'
                  : 'Não consegui enviar a foto agora. ${e.toString()}',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _removerFoto(int idx) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Remover foto?'),
        content: const Text('Essa ação não pode ser desfeita.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Remover'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref
          .read(clienteFormActionsProvider)
          .removerFoto(clienteId: widget.cliente.id, idx: idx);
      ref.invalidate(clienteDetailProvider(widget.cliente.id));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Não consegui remover a foto agora.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final fotos = widget.cliente.fotos ?? const <Map<String, dynamic>>[];

    return AppSurfaceCard(
      child: Padding(
        padding: const EdgeInsets.all(2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.photo_library_outlined,
                    size: 16, color: scheme.onSurfaceVariant),
                const SizedBox(width: 6),
                Text(
                  'FOTOS · ${fotos.length}',
                  style: TextStyle(
                    fontSize: 11,
                    letterSpacing: 0.5,
                    fontWeight: FontWeight.w700,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                FilledButton.tonalIcon(
                  onPressed: _uploading ? null : _adicionarFoto,
                  icon: _uploading
                      ? const SizedBox(
                          height: 14,
                          width: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.add_a_photo, size: 16),
                  label: const Text('Adicionar'),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(0, 36),
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (fotos.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  'Nenhuma foto. Toque em "Adicionar" pra anexar a primeira.',
                  style: TextStyle(
                    fontSize: 13,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              )
            else
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3,
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                ),
                itemCount: fotos.length,
                itemBuilder: (_, i) => _FotoTile(
                  clienteId: widget.cliente.id,
                  idx: i,
                  foto: fotos[i],
                  onTap: () => _abrirFullscreen(
                    context: context,
                    clienteId: widget.cliente.id,
                    fotos: fotos,
                    inicial: i,
                  ),
                  onLongPress: () => _removerFoto(i),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _FotoTile extends ConsumerWidget {
  final String clienteId;
  final int idx;
  final Map<String, dynamic> foto;
  final VoidCallback onTap;
  final VoidCallback onLongPress;

  const _FotoTile({
    required this.clienteId,
    required this.idx,
    required this.foto,
    required this.onTap,
    required this.onLongPress,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tipo = (foto['tipo'] ?? 'outro') as String;
    final info = _tipoInfo(tipo);

    return GestureDetector(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Stack(
        children: [
          _FotoNetworkImage(
            clienteId: clienteId,
            idx: idx,
            fit: BoxFit.cover,
            borderRadius: BorderRadius.circular(8),
          ),
          Positioned(
            left: 4,
            top: 4,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
              decoration: BoxDecoration(
                color: info.color.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(info.icon, size: 9, color: Colors.white),
                  const SizedBox(width: 2),
                  Text(
                    info.label,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FotoNetworkImage extends ConsumerStatefulWidget {
  final String clienteId;
  final int idx;
  final BoxFit fit;
  final BorderRadius? borderRadius;
  const _FotoNetworkImage({
    required this.clienteId,
    required this.idx,
    required this.fit,
    this.borderRadius,
  });

  @override
  ConsumerState<_FotoNetworkImage> createState() => _FotoNetworkImageState();
}

class _FotoNetworkImageState extends ConsumerState<_FotoNetworkImage> {
  String? _token;

  @override
  void initState() {
    super.initState();
    readAccessToken().then((t) {
      if (mounted) setState(() => _token = t);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_token == null) {
      return Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHigh,
          borderRadius: widget.borderRadius,
        ),
      );
    }
    final url =
        '$apiBaseUrl/api/v1/clientes-campo/${widget.clienteId}/foto/${widget.idx}';
    final image = Image.network(
      url,
      fit: widget.fit,
      headers: {'Authorization': 'Bearer $_token'},
      errorBuilder: (_, __, ___) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerHigh,
        child: const Center(
          child: Icon(Icons.broken_image, size: 24, color: Colors.grey),
        ),
      ),
      loadingBuilder: (_, child, progress) {
        if (progress == null) return child;
        return Container(
          color: Theme.of(context).colorScheme.surfaceContainerHigh,
          child: const Center(
            child: SizedBox(
              height: 18,
              width: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        );
      },
    );
    if (widget.borderRadius == null) return image;
    return ClipRRect(borderRadius: widget.borderRadius!, child: image);
  }
}

class _AdicionarFotoSheet extends StatefulWidget {
  const _AdicionarFotoSheet();

  @override
  State<_AdicionarFotoSheet> createState() => _AdicionarFotoSheetState();
}

class _AdicionarFotoSheetState extends State<_AdicionarFotoSheet> {
  String _tipo = 'instalacao';

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
            'Adicionar foto',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Escolha o tipo:',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _tipos
                .map(
                  (t) => ChoiceChip(
                    label: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(t.icon, size: 14, color: t.color),
                        const SizedBox(width: 4),
                        Text(t.label),
                      ],
                    ),
                    selected: _tipo == t.key,
                    onSelected: (_) => setState(() => _tipo = t.key),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  icon: const Icon(Icons.photo_camera),
                  label: const Text('Câmera'),
                  onPressed: () => Navigator.pop(
                    context,
                    (source: ImageSource.camera, tipo: _tipo),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.tonalIcon(
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Galeria'),
                  onPressed: () => Navigator.pop(
                    context,
                    (source: ImageSource.gallery, tipo: _tipo),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }
}

void _abrirFullscreen({
  required BuildContext context,
  required String clienteId,
  required List<Map<String, dynamic>> fotos,
  required int inicial,
}) {
  Navigator.push(
    context,
    MaterialPageRoute(
      builder: (_) => _FotoFullscreenViewer(
        clienteId: clienteId,
        fotos: fotos,
        inicial: inicial,
      ),
    ),
  );
}

class _FotoFullscreenViewer extends StatefulWidget {
  final String clienteId;
  final List<Map<String, dynamic>> fotos;
  final int inicial;

  const _FotoFullscreenViewer({
    required this.clienteId,
    required this.fotos,
    required this.inicial,
  });

  @override
  State<_FotoFullscreenViewer> createState() => _FotoFullscreenViewerState();
}

class _FotoFullscreenViewerState extends State<_FotoFullscreenViewer> {
  late final PageController _pc;
  late int _idx;

  @override
  void initState() {
    super.initState();
    _idx = widget.inicial;
    _pc = PageController(initialPage: widget.inicial);
  }

  @override
  void dispose() {
    _pc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final foto = widget.fotos[_idx];
    final tipo = (foto['tipo'] ?? 'outro') as String;
    final info = _tipoInfo(tipo);
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Row(
          children: [
            Icon(info.icon, size: 16, color: info.color),
            const SizedBox(width: 6),
            Text(info.label, style: const TextStyle(fontSize: 15)),
            const SizedBox(width: 12),
            Text(
              '${_idx + 1} / ${widget.fotos.length}',
              style: const TextStyle(fontSize: 13, color: Colors.white70),
            ),
          ],
        ),
      ),
      body: PageView.builder(
        controller: _pc,
        itemCount: widget.fotos.length,
        onPageChanged: (i) => setState(() => _idx = i),
        itemBuilder: (_, i) => InteractiveViewer(
          minScale: 1.0,
          maxScale: 4.0,
          child: Center(
            child: _FotoNetworkImage(
              clienteId: widget.clienteId,
              idx: i,
              fit: BoxFit.contain,
            ),
          ),
        ),
      ),
    );
  }
}
