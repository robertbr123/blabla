import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import 'rede_data.dart';

class RedeScreen extends ConsumerStatefulWidget {
  const RedeScreen({super.key, required this.clienteId});
  final String clienteId;

  @override
  ConsumerState<RedeScreen> createState() => _RedeScreenState();
}

class _RedeScreenState extends ConsumerState<RedeScreen> {
  final _senha = TextEditingController();
  final _serial = TextEditingController();
  bool _enviando = false;

  @override
  void dispose() {
    _senha.dispose();
    _serial.dispose();
    super.dispose();
  }

  Future<void> _trocar(bool precisaSerial) async {
    final senha = _senha.text.trim();
    if (senha.length < 8 || senha.length > 63) {
      _msg('A senha deve ter de 8 a 63 caracteres.');
      return;
    }
    if (precisaSerial && _serial.text.trim().isEmpty) {
      _msg('Informe o serial da ONU.');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Trocar senha do WiFi'),
        content: const Text(
          'A internet do cliente vai reiniciar e voltar em cerca de 2 minutos. Continuar?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Trocar')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _enviando = true);
    try {
      final dio = ref.read(apiClientProvider);
      final aviso = await trocarSenhaWifi(
        dio,
        clienteId: widget.clienteId,
        senha: senha,
        serial: precisaSerial ? _serial.text.trim() : null,
      );
      if (mounted) _msg(aviso);
    } catch (e) {
      if (mounted) _msg('Falha ao trocar a senha. Tente novamente.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _msg(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(redeStatusProvider(widget.clienteId));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Rede do cliente'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar',
            onPressed: () => ref.invalidate(redeStatusProvider(widget.clienteId)),
          ),
        ],
      ),
      body: status.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Erro ao carregar a rede.'),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: () =>
                    ref.invalidate(redeStatusProvider(widget.clienteId)),
                child: const Text('Tentar novamente'),
              ),
            ],
          ),
        ),
        data: _body,
      ),
    );
  }

  Widget _body(StatusRede s) {
    final precisaSerial = !s.encontrada;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (s.encontrada) ...[
          Row(children: [
            Icon(s.online ? Icons.wifi : Icons.wifi_off,
                color: s.online ? Colors.green : Colors.grey),
            const SizedBox(width: 8),
            Text(s.online ? 'Online' : 'Offline',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const Spacer(),
            Text(s.modelo ?? ''),
          ]),
          const SizedBox(height: 8),
          const Text('Redes WiFi ativas:'),
          for (final r in s.redes.where((r) => r.enabled))
            ListTile(leading: const Icon(Icons.router), title: Text(r.ssid), dense: true),
        ] else ...[
          const Text(
            'Não localizei a ONU pelo cadastro. Informe o serial da etiqueta:',
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _serial,
            decoration: const InputDecoration(
                labelText: 'Serial da ONU', border: OutlineInputBorder()),
          ),
        ],
        const Divider(height: 32),
        TextField(
          controller: _senha,
          decoration: const InputDecoration(
            labelText: 'Nova senha do WiFi (8 a 63 caracteres)',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        // Bloqueia so se a ONU foi encontrada mas esta offline (GenieACS nao
        // alcanca). Se !encontrada, o tecnico informa o serial e tenta mesmo assim.
        FilledButton.icon(
          onPressed: (s.encontrada && !s.online) || _enviando
              ? null
              : () => _trocar(precisaSerial),
          icon: _enviando
              ? const SizedBox(
                  width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.lock_reset),
          label: const Text('Trocar senha do WiFi'),
        ),
        if (s.encontrada && !s.online)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('Aparelho offline. Tente quando voltar.',
                style: TextStyle(color: Colors.grey)),
          ),
      ],
    );
  }
}
