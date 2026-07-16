import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/dto.dart';
import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/contrato/contrato_atual_provider.dart';
import '../../../core/ui/capa_folha.dart';
import '../../../core/ui/formatters.dart';
import '../../../core/ui/pressable_scale.dart';
import '../../notificacoes/widgets/notif_bell.dart';
import 'connection_status_pill.dart';
import 'contrato_switcher.dart';

/// Capa ciano da home: saudação + sino + bloco de status integrado
/// (conexão, plano, aparelhos conectados, atalho Minha rede) + linha de
/// endereço/troca de contrato. Absorve o conteúdo do antigo topo do
/// HeroCard e do RedeDestaqueCard.
class HomeCapa extends ConsumerWidget {
  const HomeCapa({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contratoAtual = me.contratos.isEmpty ? null : _contratoAtual(ref);
    return CapaBackground(
      padding: EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        MediaQuery.paddingOf(context).top + BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceLg + BrandTokens.radiusFolha,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      saudacao(DateTime.now()),
                      style: TextStyle(
                        color: BrandTokens.capaInk.withValues(alpha: 0.65),
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      '${_primeiroNome(me.nome)} 👋',
                      style: BrandTokens.displayGreeting,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const NotifBell(),
            ],
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          _StatusBlock(me: me),
          if (contratoAtual != null &&
              contratoAtual.enderecoResumido.isNotEmpty)
            _ContratoLinha(
              contrato: contratoAtual,
              podeTrocar: me.temMultiContrato,
              onTrocar: () => showContratoSelector(context, ref, me),
            ),
        ],
      ),
    );
  }

  ContratoResumoDto _contratoAtual(WidgetRef ref) {
    final id = ref.watch(contratoAtualProvider);
    return me.contratos.firstWhere(
      (c) => c.id == id,
      orElse: () => me.contratos.first,
    );
  }

  String _primeiroNome(String full) {
    final t = full.trim();
    if (t.isEmpty) return 'Cliente';
    final p = t.split(RegExp(r'\s+')).first;
    if (p.isEmpty) return 'Cliente';
    return p[0].toUpperCase() + p.substring(1).toLowerCase();
  }
}

/// Bloco translúcido com status da conexão + plano + linha de rede.
/// Degradê gracioso: sem dados de rede (ONU não mapeada ou erro), mostra
/// só status + plano — o acesso à rede continua nas ações rápidas.
class _StatusBlock extends ConsumerWidget {
  const _StatusBlock({required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final redeAsync = ref.watch(redeAparelhosProvider);
    final rede = redeAsync.maybeWhen(
      data: (d) => d.encontrada ? d : null,
      orElse: () => null,
    );
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceMd),
      decoration: BoxDecoration(
        color: BrandTokens.capaInk.withValues(alpha: 0.22),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const ConnectionStatusPill(),
              const SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Text(
                  me.planoNome ?? 'Sem plano vinculado',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          if (rede != null) ...[
            const SizedBox(height: BrandTokens.spaceSm),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '📱 ${rede.aparelhos.length} '
                    '${rede.aparelhos.length == 1 ? "aparelho" : "aparelhos"}'
                    ' · sinal ${_saudeLabel(rede.saude)}',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                PressableScale(
                  onTap: () => context.push('/rede'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: BrandTokens.spaceSm + 2,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.22),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Text(
                      'Minha rede →',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _saudeLabel(String saude) => switch (saude) {
        'excelente' => 'Ótimo',
        'boa' => 'Bom',
        'fraca' => 'Fraco',
        _ => 'Ativo',
      };
}

/// Linha de endereço do contrato na capa; clicável quando multi-contrato.
class _ContratoLinha extends StatelessWidget {
  const _ContratoLinha({
    required this.contrato,
    required this.podeTrocar,
    required this.onTrocar,
  });
  final ContratoResumoDto contrato;
  final bool podeTrocar;
  final VoidCallback onTrocar;

  @override
  Widget build(BuildContext context) {
    final linha = Padding(
      padding: const EdgeInsets.only(top: BrandTokens.spaceSm),
      child: Row(
        children: [
          Icon(Icons.location_on_outlined,
              size: 14, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              contrato.enderecoResumido,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: BrandTokens.capaInk.withValues(alpha: 0.7),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (podeTrocar)
            Icon(Icons.swap_horiz_rounded,
                size: 16, color: BrandTokens.capaInk.withValues(alpha: 0.7)),
        ],
      ),
    );
    if (!podeTrocar) return linha;
    return GestureDetector(onTap: onTrocar, child: linha);
  }
}
