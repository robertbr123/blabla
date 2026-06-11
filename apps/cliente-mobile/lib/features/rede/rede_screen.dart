import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/rede_repository.dart';
import '../../core/branding/brand_tokens.dart';
import '../../core/contrato/contrato_atual_provider.dart';
import '../../core/ui/glass_app_bar.dart';

enum _Fase { editando, enviando, reconectando, pronto }

class RedeScreen extends ConsumerStatefulWidget {
  const RedeScreen({super.key});

  @override
  ConsumerState<RedeScreen> createState() => _RedeScreenState();
}

class _RedeScreenState extends ConsumerState<RedeScreen> {
  final _senha = TextEditingController();
  final _confirma = TextEditingController();
  bool _obscure = true;
  _Fase _fase = _Fase.editando;
  String? _erro;

  @override
  void dispose() {
    _senha.dispose();
    _confirma.dispose();
    super.dispose();
  }

  String? _validar() {
    final s = _senha.text;
    if (s.length < 8 || s.length > 63) {
      return 'A senha precisa ter de 8 a 63 caracteres.';
    }
    if (s != _confirma.text) return 'As senhas não são iguais.';
    return null;
  }

  Future<void> _confirmarTroca() async {
    final erro = _validar();
    if (erro != null) {
      setState(() => _erro = erro);
      return;
    }
    setState(() => _erro = null);

    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _ConfirmSheet(),
    );
    if (ok != true || !mounted) return;

    setState(() => _fase = _Fase.enviando);
    try {
      final contratoId = ref.read(contratoAtualProvider);
      final res = await ref
          .read(redeRepositoryProvider)
          .trocarSenha(_senha.text, contratoId: contratoId);
      if (!mounted) return;
      setState(() => _fase = res.reiniciando ? _Fase.reconectando : _Fase.pronto);
    } on CooldownException catch (e) {
      if (!mounted) return;
      setState(() => _fase = _Fase.editando);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Você trocou a senha há pouco. Aguarde ~${e.minutosRestantes} min pra trocar de novo.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _fase = _Fase.editando);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não conseguimos trocar a senha agora. Tente mais tarde.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(redeStatusProvider);
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: GlassAppBar(title: 'Minha Rede WiFi'),
      body: RefreshIndicator(
        edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight,
        onRefresh: () async {
          ref.invalidate(redeStatusProvider);
          ref.invalidate(redeAparelhosProvider);
          await ref.read(redeStatusProvider.future);
        },
        child: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const _EmConstrucao(
            titulo: 'Não conseguimos carregar agora',
            texto: 'Tente novamente em instantes.',
          ),
          data: (st) {
            if (!st.encontrada) {
              return const _EmConstrucao(
                titulo: 'Gerenciamento do WiFi a caminho 🛠️',
                texto:
                    'Estamos preparando o controle do seu WiFi por aqui. Em breve '
                    'você vai poder trocar a senha da sua rede direto pelo app.',
              );
            }
            if (_fase == _Fase.reconectando) return const _Reconectando();
            if (_fase == _Fase.pronto) {
              return _Sucesso(onVoltar: () => context.pop());
            }
            return _FormTroca(
              rede: st,
              senha: _senha,
              confirma: _confirma,
              obscure: _obscure,
              erro: _erro,
              enviando: _fase == _Fase.enviando,
              onToggleObscure: () => setState(() => _obscure = !_obscure),
              onTrocar: _confirmarTroca,
            );
          },
        ),
      ),
    );
  }
}

class _FormTroca extends StatelessWidget {
  const _FormTroca({
    required this.rede,
    required this.senha,
    required this.confirma,
    required this.obscure,
    required this.erro,
    required this.enviando,
    required this.onToggleObscure,
    required this.onTrocar,
  });

  final RedeStatusDto rede;
  final TextEditingController senha;
  final TextEditingController confirma;
  final bool obscure;
  final String? erro;
  final bool enviando;
  final VoidCallback onToggleObscure;
  final VoidCallback onTrocar;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceLg,
      ),
      children: [
        _HeroRede(rede: rede),
        const SizedBox(height: BrandTokens.spaceLg),
        Container(
          padding: const EdgeInsets.all(BrandTokens.spaceLg),
          decoration: BoxDecoration(
            color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            border: Border.all(color: isDark ? Colors.white12 : BrandTokens.divider),
            boxShadow: BrandTokens.elevation1,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Trocar senha do WiFi',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: senha,
                obscureText: obscure,
                decoration: InputDecoration(
                  labelText: 'Nova senha',
                  suffixIcon: IconButton(
                    icon: Icon(obscure ? Icons.visibility_off : Icons.visibility),
                    onPressed: onToggleObscure,
                  ),
                ),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              TextField(
                controller: confirma,
                obscureText: obscure,
                decoration: const InputDecoration(labelText: 'Confirmar senha'),
              ),
              if (erro != null) ...[
                const SizedBox(height: BrandTokens.spaceSm),
                Text(erro!, style: const TextStyle(color: BrandTokens.danger, fontSize: 13)),
              ],
              const SizedBox(height: BrandTokens.spaceSm),
              const Text(
                'Esta senha vale para suas duas redes (2.4GHz e 5GHz). '
                'De 8 a 63 caracteres. Ao trocar, sua internet reinicia por ~2 min.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: BrandTokens.spaceMd),
              FilledButton.icon(
                onPressed: enviando ? null : onTrocar,
                icon: enviando
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.lock_reset_rounded, size: 18),
                label: Text(enviando ? 'Enviando…' : 'Trocar senha do WiFi'),
              ),
            ],
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        const _SaudeEDispositivos(),
      ],
    );
  }
}

class _HeroRede extends StatelessWidget {
  const _HeroRede({required this.rede});
  final RedeStatusDto rede;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF14B8B0), Color(0xFF22E0A1)],
        ),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        boxShadow: BrandTokens.elevation2,
      ),
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white.withOpacity(0.3), width: 2),
            ),
            child: const Icon(Icons.wifi_rounded, color: Colors.white, size: 32),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  rede.nomeRede,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  rede.online ? 'Sua rede está online' : 'Rede fora do ar no momento',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ConfirmSheet extends StatelessWidget {
  const _ConfirmSheet();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(BrandTokens.radiusXl)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.warning_amber_rounded, color: BrandTokens.warning, size: 40),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Sua internet vai reiniciar',
              textAlign: TextAlign.center,
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Ao trocar a senha, sua conexão reinicia e volta em cerca de 2 minutos. '
              'Depois, reconecte seus aparelhos (celular, TV, etc.) com a nova senha.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14, height: 1.4),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Trocar agora'),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancelar'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Reconectando extends StatelessWidget {
  const _Reconectando();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: BrandTokens.spaceLg),
            const Text(
              'Reconectando sua rede…',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Senha enviada! Sua internet está reiniciando e volta em ~2 minutos. '
              'Seus aparelhos vão pedir a nova senha pra reconectar.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }
}

class _Sucesso extends StatelessWidget {
  const _Sucesso({required this.onVoltar});
  final VoidCallback onVoltar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_rounded, color: BrandTokens.success, size: 56),
            const SizedBox(height: BrandTokens.spaceMd),
            const Text(
              'Senha enviada!',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            const Text(
              'Use a nova senha pra reconectar seus aparelhos.',
              textAlign: TextAlign.center,
              style: TextStyle(color: BrandTokens.textSecondary, fontSize: 14),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            FilledButton(onPressed: onVoltar, child: const Text('Voltar')),
          ],
        ),
      ),
    );
  }
}

class _EmConstrucao extends StatelessWidget {
  const _EmConstrucao({required this.titulo, required this.texto});
  final String titulo;
  final String texto;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceXl,
        MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd,
        BrandTokens.spaceXl,
        BrandTokens.spaceXl,
      ),
      children: [
        Center(
          child: Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.wifi_rounded, color: BrandTokens.primary, size: 48),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        Text(
          titulo,
          textAlign: TextAlign.center,
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        Text(
          texto,
          textAlign: TextAlign.center,
          style: const TextStyle(color: BrandTokens.textSecondary, fontSize: 15, height: 1.4),
        ),
      ],
    );
  }
}

class _SaudeEDispositivos extends ConsumerWidget {
  const _SaudeEDispositivos();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(redeAparelhosProvider);
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(BrandTokens.spaceMd),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const SizedBox.shrink(),
      data: (d) {
        if (!d.encontrada) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SaudeBadge(saude: d.saude),
            const SizedBox(height: BrandTokens.spaceLg),
            _DispositivosCard(aparelhos: d.aparelhos, total: d.total),
          ],
        );
      },
    );
  }
}

class _SaudeBadge extends StatelessWidget {
  const _SaudeBadge({required this.saude});
  final String saude;

  ({Color cor, IconData icon, String label, String sub}) _ui() {
    switch (saude) {
      case 'excelente':
        return (
          cor: BrandTokens.success,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal excelente',
          sub: 'Sua fibra está com sinal ótimo.',
        );
      case 'boa':
        return (
          cor: BrandTokens.primary,
          icon: Icons.signal_cellular_alt_rounded,
          label: 'Sinal bom',
          sub: 'Sua conexão está saudável.',
        );
      case 'fraca':
        return (
          cor: BrandTokens.warning,
          icon: Icons.signal_cellular_alt_2_bar_rounded,
          label: 'Sinal fraco',
          sub: 'Pode valer a pena falar com o suporte.',
        );
      default:
        return (
          cor: BrandTokens.info,
          icon: Icons.wifi_tethering_rounded,
          label: 'Conexão ativa',
          sub: 'Sua rede está no ar.',
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ui = _ui();
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: ui.cor.withOpacity(0.10),
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: ui.cor.withOpacity(0.30)),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: ui.cor.withOpacity(0.16),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: Icon(ui.icon, color: ui.cor, size: 22),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(ui.label,
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: ui.cor)),
                Text(ui.sub,
                    style: const TextStyle(color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
          if (saude == 'fraca')
            TextButton(
              onPressed: () => context.push('/suporte/novo'),
              child: const Text('Suporte'),
            ),
        ],
      ),
    );
  }
}

class _DispositivosCard extends StatelessWidget {
  const _DispositivosCard({required this.aparelhos, required this.total});
  final List<RedeAparelho> aparelhos;
  final int total;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? BrandTokens.surfaceDark : BrandTokens.surface,
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        border: Border.all(color: isDark ? Colors.white12 : BrandTokens.divider),
        boxShadow: BrandTokens.elevation1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(BrandTokens.spaceMd),
            child: Text(
              'Dispositivos conectados ($total)',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
          ),
          if (aparelhos.isEmpty)
            const Padding(
              padding: EdgeInsets.fromLTRB(
                  BrandTokens.spaceMd, 0, BrandTokens.spaceMd, BrandTokens.spaceMd),
              child: Text(
                'Nenhum aparelho conectado agora.',
                style: TextStyle(color: BrandTokens.textSecondary, fontSize: 13),
              ),
            )
          else
            ...aparelhos.map((a) => _DispositivoRow(aparelho: a)),
        ],
      ),
    );
  }
}

class _DispositivoRow extends StatelessWidget {
  const _DispositivoRow({required this.aparelho});
  final RedeAparelho aparelho;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: BrandTokens.spaceMd, vertical: BrandTokens.spaceSm),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
            ),
            child: const Icon(Icons.devices_other_rounded,
                color: BrandTokens.primary, size: 18),
          ),
          const SizedBox(width: BrandTokens.spaceMd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(aparelho.nomeExibicao,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
                if (aparelho.ip.isNotEmpty)
                  Text(aparelho.ip,
                      style: const TextStyle(
                          color: BrandTokens.textSecondary, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
