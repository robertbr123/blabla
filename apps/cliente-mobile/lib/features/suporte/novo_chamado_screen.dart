import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/os_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/haptics.dart';

/// Wizard 3 steps: tipo -> detalhes -> confirma.
class NovoChamadoScreen extends ConsumerStatefulWidget {
  const NovoChamadoScreen({super.key});

  @override
  ConsumerState<NovoChamadoScreen> createState() => _NovoChamadoScreenState();
}

class _NovoChamadoScreenState extends ConsumerState<NovoChamadoScreen> {
  int _step = 0;
  String? _tipo;
  final _descCtrl = TextEditingController();
  final _extraCtrl = TextEditingController(); // depende do tipo
  bool _loading = false;

  @override
  void dispose() {
    _descCtrl.dispose();
    _extraCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Novo chamado'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline_rounded),
            tooltip: 'Perguntas frequentes',
            onPressed: () => context.push('/faq'),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            children: [
              _StepIndicator(current: _step, total: 3),
              const SizedBox(height: BrandTokens.spaceLg),
              Expanded(
                child: switch (_step) {
                  0 => _StepTipo(
                      selected: _tipo,
                      onSelect: (t) => setState(() {
                        _tipo = t;
                        _step = 1;
                      }),
                    ),
                  1 => _StepDetalhes(
                      tipo: _tipo!,
                      descCtrl: _descCtrl,
                      extraCtrl: _extraCtrl,
                    ),
                  _ => _StepConfirma(
                      tipo: _tipo!,
                      descricao: _descCtrl.text,
                      extra: _extraCtrl.text,
                    ),
                },
              ),
              if (_step > 0)
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _loading
                            ? null
                            : () => setState(() => _step--),
                        child: const Text('Voltar'),
                      ),
                    ),
                    const SizedBox(width: BrandTokens.spaceMd),
                    Expanded(
                      child: FilledButton(
                        onPressed: _loading ? null : _next,
                        child: _loading
                            ? const SizedBox(
                                height: 22,
                                width: 22,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Text(_step == 2 ? 'Confirmar' : 'Continuar'),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _next() async {
    if (_step == 1) {
      if (_descCtrl.text.trim().isEmpty) {
        _toast('Descreva o problema');
        return;
      }
      setState(() => _step = 2);
      return;
    }
    // _step == 2 → submit
    setState(() => _loading = true);
    final payload = <String, dynamic>{};
    if (_tipo == 'mudanca_endereco') {
      payload['novo_endereco'] = _extraCtrl.text;
    } else if (_tipo == 'troca_plano') {
      payload['plano_desejado'] = _extraCtrl.text;
    }
    try {
      await ref.read(osRepositoryProvider).criar(
            tipo: _tipo!,
            descricao: _descCtrl.text.trim(),
            payload: payload,
          );
      ref.invalidate(osListProvider);
      if (!mounted) return;
      await Haptics.success();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Chamado aberto. Em breve entramos em contato.')),
      );
      context.pop();
    } catch (_) {
      if (!mounted) return;
      _toast('Falha ao abrir chamado. Tente de novo.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));
}

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({required this.current, required this.total});
  final int current;
  final int total;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(total, (i) {
        final active = i <= current;
        return Expanded(
          child: Container(
            height: 4,
            margin: EdgeInsets.only(right: i < total - 1 ? BrandTokens.spaceXs : 0),
            decoration: BoxDecoration(
              color: active ? BrandTokens.primary : BrandTokens.divider,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}

class _StepTipo extends StatelessWidget {
  const _StepTipo({required this.selected, required this.onSelect});
  final String? selected;
  final void Function(String) onSelect;

  @override
  Widget build(BuildContext context) {
    final opts = const [
      ('sem_internet', Icons.wifi_off_outlined, 'Sem internet',
          'Internet caiu, lenta ou intermitente'),
      ('mudanca_endereco', Icons.home_outlined, 'Mudanca de endereco',
          'Levar o plano pra outro endereco'),
      ('troca_plano', Icons.swap_horiz, 'Troca de plano',
          'Subir, descer ou mudar o plano contratado'),
    ];
    return ListView(
      children: [
        Text(
          'Qual o motivo?',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        for (final (id, icon, title, sub) in opts) ...[
          _OpcaoCard(
            icon: icon,
            title: title,
            subtitle: sub,
            selected: selected == id,
            onTap: () => onSelect(id),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
        ],
      ],
    );
  }
}

class _OpcaoCard extends StatelessWidget {
  const _OpcaoCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });
  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
      child: Container(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
          border: Border.all(
            color: selected ? BrandTokens.primary : BrandTokens.divider,
            width: selected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 28, color: BrandTokens.primary),
            const SizedBox(width: BrandTokens.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: BrandTokens.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: BrandTokens.textSecondary),
          ],
        ),
      ),
    );
  }
}

class _StepDetalhes extends StatelessWidget {
  const _StepDetalhes({
    required this.tipo,
    required this.descCtrl,
    required this.extraCtrl,
  });
  final String tipo;
  final TextEditingController descCtrl;
  final TextEditingController extraCtrl;

  @override
  Widget build(BuildContext context) {
    final tituloExtra = switch (tipo) {
      'mudanca_endereco' => 'Novo endereco (rua, numero, bairro)',
      'troca_plano' => 'Plano desejado',
      _ => null,
    };
    return ListView(
      children: [
        Text(
          'Conta um pouco mais',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        TextField(
          controller: descCtrl,
          maxLines: 4,
          maxLength: 2000,
          decoration: const InputDecoration(
            labelText: 'O que esta acontecendo?',
            alignLabelWithHint: true,
          ),
        ),
        if (tituloExtra != null) ...[
          const SizedBox(height: BrandTokens.spaceMd),
          TextField(
            controller: extraCtrl,
            decoration: InputDecoration(labelText: tituloExtra),
          ),
        ],
      ],
    );
  }
}

class _StepConfirma extends StatelessWidget {
  const _StepConfirma({
    required this.tipo,
    required this.descricao,
    required this.extra,
  });
  final String tipo;
  final String descricao;
  final String extra;

  @override
  Widget build(BuildContext context) {
    final tipoLabel = switch (tipo) {
      'sem_internet' => 'Sem internet',
      'mudanca_endereco' => 'Mudanca de endereco',
      'troca_plano' => 'Troca de plano',
      _ => tipo,
    };
    return ListView(
      children: [
        Text(
          'Confere e confirma',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        _Field(label: 'Tipo', value: tipoLabel),
        _Field(label: 'Descricao', value: descricao),
        if (extra.isNotEmpty)
          _Field(
            label: tipo == 'mudanca_endereco' ? 'Novo endereco' : 'Plano desejado',
            value: extra,
          ),
        const SizedBox(height: BrandTokens.spaceLg),
        Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: BrandTokens.info.withOpacity(0.08),
            borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
          ),
          child: const Text(
            'Apos confirmar, nosso time entra em contato pra dar andamento.',
            style: TextStyle(color: BrandTokens.textPrimary),
          ),
        ),
      ],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: BrandTokens.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}
