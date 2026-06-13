import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/ui/formatters.dart';
import '../../core/ui/glass_app_bar.dart';

class EditarPerfilScreen extends ConsumerStatefulWidget {
  const EditarPerfilScreen({
    super.key,
    required this.campo,
    required this.valor,
  });
  final String campo; // 'telefone' | 'email'
  final String valor;

  @override
  ConsumerState<EditarPerfilScreen> createState() => _EditarPerfilScreenState();
}

class _EditarPerfilScreenState extends ConsumerState<EditarPerfilScreen> {
  late final TextEditingController _ctrl;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    // Aplica mascara inicial se for telefone (valor vem do backend sem mascara).
    final v = widget.campo == 'telefone'
        ? formatTelefone(widget.valor)
        : widget.valor;
    _ctrl = TextEditingController(text: v);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _loading = true);
    try {
      final repo = ref.read(meRepositoryProvider);
      if (widget.campo == 'telefone') {
        // Backend recebe so digitos — strip da mascara.
        final digits = _ctrl.text.replaceAll(RegExp(r'\D'), '');
        await repo.patchMe(telefone: digits);
      } else {
        await repo.patchMe(email: _ctrl.text);
      }
      ref.invalidate(meProvider);
      if (!mounted) return;
      context.pop();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao salvar')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.campo == 'telefone' ? 'Telefone' : 'Email';
    final keyboardType = widget.campo == 'telefone'
        ? TextInputType.phone
        : TextInputType.emailAddress;
    return Scaffold(
      appBar: GlassAppBar(title: label),
      extendBodyBehindAppBar: true,
      body: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            children: [
              SizedBox(
                height: MediaQuery.paddingOf(context).top +
                    kToolbarHeight +
                    BrandTokens.spaceMd,
              ),
              TextField(
                controller: _ctrl,
                keyboardType: keyboardType,
                autofocus: true,
                inputFormatters: widget.campo == 'telefone'
                    ? [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(11),
                        TelefoneFormatter(),
                      ]
                    : null,
                decoration: InputDecoration(
                  labelText: label,
                  hintText: widget.campo == 'telefone'
                      ? '(47) 99999-8888'
                      : 'voce@exemplo.com',
                ),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _loading ? null : _save,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Salvar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
