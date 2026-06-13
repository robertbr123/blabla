import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/sync/cadastro_draft_repo.dart';
import '../../../core/sync/connectivity_status.dart';
import '../../../core/ui/app_surfaces.dart';
import '../cliente_data.dart';
import '../cliente_form_data.dart';

/// Banner clicável na lista de Clientes mostrando cadastros pendentes.
class CadastroDraftsBanner extends StatelessWidget {
  const CadastroDraftsBanner({super.key, required this.count, required this.onTap});
  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: AppSurfaceCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFFF59E0B).withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.cloud_upload_rounded,
                  size: 18, color: Color(0xFFB45309)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                '$count cadastro${count == 1 ? '' : 's'} pendente${count == 1 ? '' : 's'} de envio',
                style: const TextStyle(
                    fontWeight: FontWeight.w700, color: Color(0xFFB45309)),
              ),
            ),
            Icon(Icons.chevron_right, color: scheme.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}

Future<void> showCadastroDraftsSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => const _CadastroDraftsSheet(),
  );
}

class _CadastroDraftsSheet extends ConsumerStatefulWidget {
  const _CadastroDraftsSheet();
  @override
  ConsumerState<_CadastroDraftsSheet> createState() =>
      _CadastroDraftsSheetState();
}

class _CadastroDraftsSheetState extends ConsumerState<_CadastroDraftsSheet> {
  String? _enviandoId;

  void _toast(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _enviar(CadastroDraft d) async {
    setState(() => _enviandoId = d.id);
    try {
      await ref.read(clienteFormActionsProvider).criarFromJson(d.payload);
      await _concluir(d, 'Cliente cadastrado.');
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      final detail = (e.response?.data is Map
              ? (e.response!.data as Map)['detail']?.toString()
              : null) ??
          '';
      final dl = detail.toLowerCase();
      if (code == 409 && (dl.contains('cpf') || dl.contains('existe'))) {
        await _concluir(d, 'Cliente já estava cadastrado.');
      } else {
        _toast(detail.isNotEmpty
            ? detail
            : 'Não consegui enviar agora. Tente de novo.');
      }
    } catch (_) {
      _toast('Não consegui enviar agora. Tente de novo.');
    } finally {
      if (mounted) setState(() => _enviandoId = null);
    }
  }

  Future<void> _concluir(CadastroDraft d, String msg) async {
    await ref.read(cadastroDraftRepoProvider).delete(d.id);
    ref.invalidate(cadastroDraftsProvider);
    ref.invalidate(clientesListProvider);
    _toast(msg);
  }

  Future<void> _descartar(CadastroDraft d) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Descartar rascunho?'),
        content: Text('O cadastro de ${d.nome} não será enviado.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Descartar')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(cadastroDraftRepoProvider).delete(d.id);
    ref.invalidate(cadastroDraftsProvider);
  }

  @override
  Widget build(BuildContext context) {
    final drafts = ref.watch(cadastroDraftsProvider).value ?? const [];
    final online = ref.watch(connectivityStatusProvider).value ?? true;
    final mq = MediaQuery.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: mq.viewInsets.bottom + 16, top: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Cadastros pendentes',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          if (!online)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('Conecte-se pra enviar.',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ),
          const SizedBox(height: 12),
          Flexible(
            child: ListView.separated(
              shrinkWrap: true,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: drafts.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final d = drafts[i];
                final enviando = _enviandoId == d.id;
                return AppSurfaceCard(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(d.nome,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text('CPF ${d.cpf}',
                                style: const TextStyle(
                                    fontSize: 12, color: Colors.grey)),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Descartar',
                        icon: const Icon(Icons.delete_outline),
                        onPressed: enviando ? null : () => _descartar(d),
                      ),
                      FilledButton(
                        onPressed:
                            (online && !enviando) ? () => _enviar(d) : null,
                        child: enviando
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2))
                            : const Text('Enviar'),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
