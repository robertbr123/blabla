import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import 'rede_data.dart';

/// Traduz a falha da troca de senha numa mensagem acionável pro técnico em vez
/// do genérico "tente novamente" (que esconde se foi rede, serial ou aparelho).
String _erroTrocaSenha(DioException e) {
  final data = e.response?.data;
  final detail = data is Map ? data['detail']?.toString() : null;
  if (detail != null && detail.trim().isNotEmpty) return detail;
  final code = e.response?.statusCode;
  if (code == null) {
    return 'Sem conexão. Verifique a internet e tente de novo.';
  }
  if (code == 404) return 'ONU não localizada. Confira o serial da etiqueta.';
  if (code == 409 || code == 503 || code == 504) {
    return 'Aparelho fora do ar agora. Tente quando ele voltar online.';
  }
  return 'Falha ao trocar a senha (erro $code). Tente novamente.';
}

/// Cor do RX power (GPON, dBm). Verde -8..-25 (bom), amarelo -25..-27 (atencao),
/// vermelho < -27 ou > -8 (sinal quente demais / fraco demais).
Color _corRx(double? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}

String _fmtUptime(int? s) {
  if (s == null) return '—';
  final d = s ~/ 86400, h = (s % 86400) ~/ 3600, m = (s % 3600) ~/ 60;
  if (d > 0) return '${d}d ${h}h';
  if (h > 0) return '${h}h ${m}min';
  return '${m}min';
}

String _fmtHora(DateTime? t) {
  if (t == null) return '—';
  String dois(int n) => n.toString().padLeft(2, '0');
  return '${dois(t.hour)}:${dois(t.minute)}';
}

class RedeScreen extends ConsumerStatefulWidget {
  const RedeScreen({super.key, required this.cpf});
  final String cpf;

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
        cpf: widget.cpf,
        senha: senha,
        serial: precisaSerial ? _serial.text.trim() : null,
      );
      if (mounted) _msg(aviso);
    } on DioException catch (e) {
      if (mounted) _msg(_erroTrocaSenha(e));
    } catch (_) {
      if (mounted) _msg('Falha ao trocar a senha. Tente novamente.');
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _msg(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext context) {
    final status = ref.watch(redeStatusProvider(widget.cpf));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Rede do cliente'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Atualizar',
            onPressed: () {
              ref.invalidate(redeStatusProvider(widget.cpf));
              ref.invalidate(redeDiagnosticoProvider(widget.cpf));
            },
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
                    ref.invalidate(redeStatusProvider(widget.cpf)),
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
          const Divider(height: 32),
          _diagnostico(),
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

  Widget _diagnostico() {
    final diag = ref.watch(redeDiagnosticoProvider(widget.cpf));
    return diag.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => const Text('Não foi possível carregar o diagnóstico.',
          style: TextStyle(color: Colors.grey)),
      data: (d) {
        if (!d.encontrada) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Sinal da fibra ──
            Row(children: [
              const Icon(Icons.settings_input_antenna, size: 20),
              const SizedBox(width: 8),
              const Text('Sinal da fibra',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              const Spacer(),
              Text('última leitura: ${_fmtHora(d.lastInform)}',
                  style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ]),
            const SizedBox(height: 8),
            if (d.sinal == null)
              const Text('Sinal ainda não disponível — puxe pra atualizar (~5min).',
                  style: TextStyle(color: Colors.grey))
            else ...[
              Row(children: [
                Icon(Icons.circle, size: 12, color: _corRx(d.sinal!.rxPower)),
                const SizedBox(width: 8),
                Text('RX: ${d.sinal!.rxPower?.toStringAsFixed(1) ?? '—'} dBm'),
                const SizedBox(width: 16),
                Text('TX: ${d.sinal!.txPower?.toStringAsFixed(1) ?? '—'} dBm'),
              ]),
              const SizedBox(height: 4),
              Text('GPON: ${d.sinal!.statusGpon ?? '—'}   •   '
                  'PPPoE: ${d.sinal!.conexaoPppoe ?? '—'}'),
              if (d.sinal!.ipExterno != null) Text('IP: ${d.sinal!.ipExterno}'),
              Text('Uptime: ${_fmtUptime(d.sinal!.uptimeS)}'
                  '${d.sinal!.ultimoErro != null && d.sinal!.ultimoErro != 'ERROR_NONE' ? '   •   Último erro: ${d.sinal!.ultimoErro}' : ''}'),
            ],
            const Divider(height: 32),
            // ── Aparelhos conectados ──
            Text('Aparelhos conectados (${d.aparelhos.length})',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            if (d.aparelhos.isEmpty)
              const Text('Nenhum aparelho conectado no momento.',
                  style: TextStyle(color: Colors.grey))
            else
              for (final a in d.aparelhos)
                ListTile(
                  dense: true,
                  leading: Icon(
                      a.interface.contains('11') || a.interface.toLowerCase().contains('wifi')
                          ? Icons.wifi
                          : Icons.lan,
                      size: 20,
                      color: a.ativo ? Colors.green : Colors.grey),
                  title: Text(a.nome.isEmpty ? a.ip : a.nome),
                  subtitle: Text('${a.ip}  •  ${a.mac}'),
                ),
          ],
        );
      },
    );
  }
}
