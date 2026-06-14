import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart' show launchUrl;

import '../../core/branding/brand_status_pill.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_state_panel.dart';
import '../../core/ui/app_surfaces.dart';
import '../../core/ui/ios_glass_header.dart';
import '../os/widgets/cliente_avatar.dart';
import '../rede/rede_data.dart';
import 'cliente_data.dart';
import 'cliente_form_data.dart';
import 'widgets/cliente_fotos.dart';
import 'widgets/cliente_materiais.dart';

class ClienteDetailScreen extends ConsumerWidget {
  final String id;
  const ClienteDetailScreen({super.key, required this.id});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(clienteDetailProvider(id));
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: scheme.surface,
      body: CustomScrollView(
        slivers: [
          IosGlassHeader(
            title: 'Cliente',
            leading: BackButton(
              onPressed: () =>
                  context.canPop() ? context.pop() : context.go('/clientes'),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Atualizar',
                onPressed: () {
                  ref.invalidate(clienteDetailProvider(id));
                  ref.invalidate(clienteOsHistoricoProvider(id));
                },
              ),
            ],
          ),
          async.when(
            loading: () => const SliverFillRemaining(
              hasScrollBody: false,
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => SliverFillRemaining(
              hasScrollBody: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
                child: AppStatePanel.error(
                  title: 'Não foi possível carregar este cliente',
                  message:
                      'Os dados de detalhe não responderam como esperado. Atualize novamente em instantes.',
                  detail: e is DioException
                      ? extractDioMessage(e, fallback: '')
                      : null,
                  actionLabel: 'Tentar novamente',
                  onAction: () => ref.invalidate(clienteDetailProvider(id)),
                ),
              ),
            ),
            data: (c) => SliverToBoxAdapter(child: _Body(cliente: c)),
          ),
        ],
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  final ClienteCampo cliente;
  const _Body({required this.cliente});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final osAsync = ref.watch(clienteOsHistoricoProvider(cliente.id));

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
        AppSurfaceCard(child: _Header(cliente: cliente)),
        const SizedBox(height: 12),
        _SecaoEndereco(cliente: cliente),
        const SizedBox(height: 12),
        _SecaoConexao(cliente: cliente),
        const SizedBox(height: 12),
        _SecaoInstalacao(cliente: cliente),
        const SizedBox(height: 12),
        ClienteMateriaisSection(clienteId: cliente.id),
        if (cliente.observation != null && cliente.observation!.isNotEmpty) ...[
          const SizedBox(height: 12),
          _SecaoSimples(
            icone: Icons.notes,
            titulo: 'Observação',
            conteudo: cliente.observation!,
          ),
        ],
        const SizedBox(height: 12),
        ClienteFotosSection(cliente: cliente),
        const SizedBox(height: 12),
        AppSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const AppSectionHeader(
                title: 'Histórico de OS',
                subtitle:
                    'Ordens vinculadas a este cliente para consulta rápida em campo.',
              ),
              const SizedBox(height: 16),
              osAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (_, __) => Text(
                  'Não consegui carregar o histórico.',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                data: (lista) {
                  if (lista.isEmpty) {
                    return Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color:
                            Theme.of(context).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        cliente.sgpSyncedAt == null
                            ? 'Cliente ainda não está no SGP, então o histórico de OS ainda não apareceu por aqui.'
                            : 'Sem OS registradas para este cliente.',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          height: 1.4,
                        ),
                      ),
                    );
                  }
                  return Column(
                    children: lista.map((os) => _OsTile(os: os)).toList(),
                  );
                },
              ),
            ],
          ),
        ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final ClienteCampo cliente;
  const _Header({required this.cliente});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final synced = cliente.sgpSyncedAt != null;
    final telBr = _formatPhone(cliente.telefone);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionHeader(
          title: 'Resumo do cliente',
          subtitle:
              'Contato, sincronização e contexto principal da instalação.',
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  ClienteAvatar(nome: cliente.nome, size: 60),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Nome auto-encolhe para caber, mantendo 1-2 linhas no máximo.
                        Text(
                          cliente.nome,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: scheme.onSurface,
                            // Tamanho responsivo ao comprimento do nome
                            fontSize: cliente.nome.length > 28
                                ? 18
                                : cliente.nome.length > 22
                                    ? 20
                                    : 22,
                            fontWeight: FontWeight.w800,
                            height: 1.15,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          cliente.planNome,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 13,
                            color: scheme.onSurfaceVariant,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Pill em linha separada — não compete com o nome
              BrandStatusPill(
                label: synced ? 'SGP sincronizado' : 'Pendente SGP',
                icon: synced
                    ? Icons.cloud_done_outlined
                    : Icons.cloud_off_outlined,
                tone: synced ? BrandTone.success : BrandTone.warning,
              ),
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: scheme.surface.withValues(alpha: 0.82),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _KvCopyable(
                      icon: Icons.credit_card,
                      label: _formatCpf(cliente.cpf),
                      valueToCopy: cliente.cpf,
                    ),
                    _KvCopyable(
                      icon: Icons.phone_iphone,
                      label: telBr,
                      valueToCopy: cliente.telefone,
                      onTap: () =>
                          launchUrl(Uri.parse('tel:+55${cliente.telefone}')),
                    ),
                    if (cliente.email != null &&
                        cliente.email!.trim().isNotEmpty)
                      _KvCopyable(
                        icon: Icons.email_outlined,
                        label: cliente.email!,
                        valueToCopy: cliente.email!,
                        onTap: () =>
                            launchUrl(Uri.parse('mailto:${cliente.email!}')),
                      ),
                    if (cliente.dob.year > 1900)
                      Row(
                        children: [
                          Icon(
                            Icons.cake_outlined,
                            size: 14,
                            color: scheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            DateFormat('dd/MM/yyyy').format(cliente.dob),
                            style: TextStyle(
                              fontSize: 12.5,
                              color: scheme.onSurfaceVariant,
                            ),
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

  String _formatCpf(String cpf) {
    final d = cpf.replaceAll(RegExp(r'\D'), '');
    if (d.length == 11) {
      return '${d.substring(0, 3)}.${d.substring(3, 6)}.${d.substring(6, 9)}-${d.substring(9)}';
    }
    if (d.length == 14) {
      return '${d.substring(0, 2)}.${d.substring(2, 5)}.${d.substring(5, 8)}/${d.substring(8, 12)}-${d.substring(12)}';
    }
    return cpf;
  }

  String _formatPhone(String s) {
    final d = s.replaceAll(RegExp(r'\D'), '');
    if (d.length == 11) {
      return '(${d.substring(0, 2)}) ${d.substring(2, 7)}-${d.substring(7)}';
    }
    if (d.length == 10) {
      return '(${d.substring(0, 2)}) ${d.substring(2, 6)}-${d.substring(6)}';
    }
    return s;
  }
}

class _SecaoEndereco extends StatelessWidget {
  final ClienteCampo cliente;
  const _SecaoEndereco({required this.cliente});

  @override
  Widget build(BuildContext context) {
    final partes = <String>[
      cliente.address,
      cliente.number,
      if (cliente.complement != null && cliente.complement!.isNotEmpty)
        cliente.complement!,
      if (cliente.neighborhood != null && cliente.neighborhood!.isNotEmpty)
        cliente.neighborhood!,
      cliente.city,
      if (cliente.state != null) cliente.state!,
      if (cliente.cep != null && cliente.cep!.isNotEmpty) cliente.cep!,
    ];
    final completo = partes.join(', ');

    return _SecaoBase(
      icone: Icons.place_outlined,
      titulo: 'Endereço',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SelectableText(
            completo,
            style: const TextStyle(fontSize: 14.5, height: 1.4),
          ),
          if (cliente.latitude != null && cliente.longitude != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: OutlinedButton.icon(
                icon: const Icon(Icons.map_outlined, size: 16),
                label: const Text('Abrir no Maps'),
                onPressed: () => launchUrl(Uri.parse(
                  'https://maps.google.com/?q=${cliente.latitude},${cliente.longitude}',
                )),
              ),
            ),
        ],
      ),
    );
  }
}

class _SecaoConexao extends StatelessWidget {
  final ClienteCampo cliente;
  const _SecaoConexao({required this.cliente});

  @override
  Widget build(BuildContext context) {
    return _SecaoBase(
      icone: Icons.router,
      titulo: 'Conexão',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Linha(label: 'Plano', value: cliente.planNome),
          _Linha(
            label: 'Vencimento',
            value: 'dia ${cliente.dueDate}',
          ),
          if (cliente.pppoeUser != null)
            _LinhaCopyable(
              label: 'PPPoE login',
              value: cliente.pppoeUser!,
              mono: true,
            ),
          if (cliente.pppoePass != null)
            _LinhaCopyable(
              label: 'PPPoE senha',
              value: cliente.pppoePass!,
              mono: true,
            ),
          _SinalResumo(cpf: cliente.cpf),
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: OutlinedButton.icon(
              icon: const Icon(Icons.wifi_password, size: 18),
              label: const Text('Gerenciar rede WiFi'),
              onPressed: () => context.push('/rede/${cliente.cpf}'),
            ),
          ),
        ],
      ),
    );
  }
}

/// Régua de cor do RX (GPON, dBm) — mesma da tela de Rede.
/// (Duplicação leve; cleanup futuro pode extrair um helper compartilhado.)
Color _corRx(double? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}

String _idadeLeitura(DateTime? t) {
  if (t == null) return '—';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'agora';
  if (d.inMinutes < 60) return 'há ${d.inMinutes} min';
  if (d.inHours < 24) return 'há ${d.inHours} h';
  return 'há ${d.inDays} ${d.inDays == 1 ? 'dia' : 'dias'}';
}

/// Resumo compacto do sinal/IP no detalhe (auto-carrega via redeDiagnosticoProvider).
class _SinalResumo extends ConsumerWidget {
  final String cpf;
  const _SinalResumo({required this.cpf});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final diag = ref.watch(redeDiagnosticoProvider(cpf));

    Widget muted(String text) => Text(
          text,
          style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
        );

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: diag.when(
        loading: () => Row(
          children: [
            const SizedBox(
              height: 14,
              width: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 8),
            muted('Carregando sinal…'),
          ],
        ),
        error: (_, __) => muted('Sinal indisponível.'),
        data: (d) {
          final s = d.sinal;
          if (!d.encontrada || s == null) return muted('Sinal indisponível.');
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.circle, size: 12, color: _corRx(s.rxPower)),
                  const SizedBox(width: 8),
                  Text(
                    'RX: ${s.rxPower?.toStringAsFixed(1) ?? '—'} dBm',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 16),
                  Flexible(
                    child: Text(
                      'GPON: ${s.statusGpon ?? '—'}',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  ),
                ],
              ),
              if (s.ipExterno != null) ...[
                const SizedBox(height: 4),
                muted('IP: ${s.ipExterno}'),
              ],
              const SizedBox(height: 4),
              Text(
                'última leitura ${_idadeLeitura(d.lastInform)}',
                style: TextStyle(fontSize: 11, color: scheme.onSurfaceVariant),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _SecaoInstalacao extends StatelessWidget {
  final ClienteCampo cliente;
  const _SecaoInstalacao({required this.cliente});

  @override
  Widget build(BuildContext context) {
    return _SecaoBase(
      icone: Icons.engineering,
      titulo: 'Instalação',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Linha(label: 'Instalador', value: cliente.installerNome),
          _Linha(
            label: 'Cadastrado em',
            value: DateFormat('dd/MM/yyyy').format(cliente.registrationDate),
          ),
          if (cliente.serial != null)
            _LinhaCopyable(label: 'Serial', value: cliente.serial!, mono: true),
          if (cliente.contrato != null)
            _Linha(label: 'Contrato', value: cliente.contrato!),
        ],
      ),
    );
  }
}

class _SecaoSimples extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final String conteudo;
  const _SecaoSimples({
    required this.icone,
    required this.titulo,
    required this.conteudo,
  });
  @override
  Widget build(BuildContext context) {
    return _SecaoBase(
      icone: icone,
      titulo: titulo,
      child: SelectableText(
        conteudo,
        style: const TextStyle(fontSize: 14, height: 1.4),
      ),
    );
  }
}

class _SecaoBase extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final Widget child;
  const _SecaoBase({
    required this.icone,
    required this.titulo,
    required this.child,
  });
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AppSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: scheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(12),
                ),
                alignment: Alignment.center,
                child: Icon(icone, size: 18, color: scheme.primary),
              ),
              const SizedBox(width: 12),
              Text(
                titulo,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: scheme.onSurface,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _Linha extends StatelessWidget {
  final String label;
  final String value;
  const _Linha({required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

class _LinhaCopyable extends StatelessWidget {
  final String label;
  final String value;
  final bool mono;
  const _LinhaCopyable({
    required this.label,
    required this.value,
    this.mono = false,
  });
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        Clipboard.setData(ClipboardData(text: value));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$label copiado'),
            duration: const Duration(milliseconds: 800),
          ),
        );
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 90,
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            Expanded(
              child: Text(
                value,
                style: TextStyle(
                  fontSize: 14,
                  fontFamily: mono ? 'monospace' : null,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            Icon(
              Icons.copy,
              size: 14,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }
}

class _KvCopyable extends StatelessWidget {
  final IconData icon;
  final String label;
  final String valueToCopy;
  final VoidCallback? onTap;
  const _KvCopyable({
    required this.icon,
    required this.label,
    required this.valueToCopy,
    this.onTap,
  });
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap ??
          () {
            Clipboard.setData(ClipboardData(text: valueToCopy));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('copiado'),
                duration: Duration(milliseconds: 800),
              ),
            );
          },
      onLongPress: () {
        Clipboard.setData(ClipboardData(text: valueToCopy));
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            Icon(icon,
                size: 13,
                color: Theme.of(context).colorScheme.onSurfaceVariant),
            const SizedBox(width: 6),
            Text(label, style: const TextStyle(fontSize: 13)),
          ],
        ),
      ),
    );
  }
}

class _OsTile extends StatelessWidget {
  final ClienteOsHistorico os;
  const _OsTile({required this.os});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final cor = switch (os.status) {
      'pendente' => const Color(0xFFf59e0b),
      'em_andamento' => const Color(0xFF2563eb),
      'concluida' => const Color(0xFF16a34a),
      'cancelada' => const Color(0xFF6b7280),
      _ => scheme.onSurfaceVariant,
    };
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 44,
            decoration: BoxDecoration(
              color: cor,
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    Text(
                      os.codigo,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: cor.withValues(alpha: 0.13),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        os.status,
                        style: TextStyle(
                          fontSize: 10,
                          color: cor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  os.problema,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13,
                    color: scheme.onSurfaceVariant,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
          if (os.concluidaEm != null) ...[
            const SizedBox(width: 12),
            Text(
              DateFormat('dd/MM').format(os.concluidaEm!),
              style: TextStyle(
                fontSize: 11,
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
