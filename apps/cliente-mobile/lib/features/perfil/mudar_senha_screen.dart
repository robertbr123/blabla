import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/me_repository.dart';
import '../../core/branding/brand_tokens.dart';

class MudarSenhaScreen extends ConsumerStatefulWidget {
  const MudarSenhaScreen({super.key});

  @override
  ConsumerState<MudarSenhaScreen> createState() => _MudarSenhaScreenState();
}

class _MudarSenhaScreenState extends ConsumerState<MudarSenhaScreen> {
  final _atual = TextEditingController();
  final _nova = TextEditingController();
  final _conf = TextEditingController();
  bool _loading = false;
  bool _hide = true;

  @override
  void dispose() {
    _atual.dispose();
    _nova.dispose();
    _conf.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_nova.text.length < 8) {
      _toast('Senha nova precisa ter ao menos 8 caracteres');
      return;
    }
    if (_nova.text != _conf.text) {
      _toast('Senhas não conferem');
      return;
    }
    setState(() => _loading = true);
    final ok = await ref.read(meRepositoryProvider).changePassword(
          currentPassword: _atual.text,
          newPassword: _nova.text,
        );
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      _toast('Senha atualizada');
      context.pop();
    } else {
      _toast('Senha atual incorreta');
    }
  }

  void _toast(String s) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mudar senha')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          child: Column(
            children: [
              TextField(
                controller: _atual,
                obscureText: _hide,
                decoration: InputDecoration(
                  labelText: 'Senha atual',
                  suffixIcon: IconButton(
                    icon:
                        Icon(_hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _nova,
                obscureText: _hide,
                decoration: const InputDecoration(labelText: 'Nova senha'),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: _conf,
                obscureText: _hide,
                decoration:
                    const InputDecoration(labelText: 'Confirme a nova senha'),
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
                    : const Text('Atualizar senha'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
