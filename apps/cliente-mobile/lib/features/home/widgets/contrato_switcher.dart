import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/conexao_repository.dart';
import '../../../core/api/dto.dart';
import '../../../core/api/me_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/contrato/contrato_atual_provider.dart';

/// Chip clicável no header da Home quando o cliente tem 2+ contratos.
/// Mostra o apelido do contrato atual; tap abre bottom sheet com a lista.
///
/// Some completamente quando `me.contratos.length <= 1`.
class ContratoSwitcher extends ConsumerWidget {
  const ContratoSwitcher({super.key, required this.me});
  final MeDto me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!me.temMultiContrato) return const SizedBox.shrink();
    final selecionadoId = ref.watch(contratoAtualProvider);
    final atual = me.contratos.firstWhere(
      (c) => c.id == selecionadoId,
      orElse: () => me.contratos.first,
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      child: Align(
        alignment: Alignment.centerLeft,
        child: InkWell(
          borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
          onTap: () => _abrir(context, ref),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: BrandTokens.spaceSm,
            ),
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.10),
              borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
              border: Border.all(
                color: BrandTokens.primary.withOpacity(0.25),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.home_rounded,
                  size: 18,
                  color: BrandTokens.primary,
                ),
                const SizedBox(width: BrandTokens.spaceSm),
                Text(
                  atual.apelidoCurto,
                  style: const TextStyle(
                    color: BrandTokens.primary,
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(width: 4),
                const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: 18,
                  color: BrandTokens.primary,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _abrir(BuildContext context, WidgetRef ref) async {
    final selecionadoId = ref.read(contratoAtualProvider);
    final novoId = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _ContratoBottomSheet(
        contratos: me.contratos,
        selecionadoId: selecionadoId ?? me.contratos.first.id,
      ),
    );
    if (novoId == null) return;
    await ref.read(contratoAtualProvider.notifier).selecionar(novoId);
    // Invalida tudo que depende de contrato_id pra refazer fetch.
    ref.invalidate(meProvider);
    ref.invalidate(conexaoProvider);
  }
}

class _ContratoBottomSheet extends StatelessWidget {
  const _ContratoBottomSheet({
    required this.contratos,
    required this.selecionadoId,
  });
  final List<ContratoResumoDto> contratos;
  final String selecionadoId;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(BrandTokens.radiusXl),
        ),
      ),
      padding: const EdgeInsets.fromLTRB(
        BrandTokens.spaceLg,
        BrandTokens.spaceMd,
        BrandTokens.spaceLg,
        BrandTokens.spaceLg,
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
                color: Colors.black.withOpacity(0.12),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: BrandTokens.spaceLg),
          const Text(
            'Escolha o contrato',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: BrandTokens.primaryDark,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceXs),
          const Text(
            'Os dados de plano e conexão vão refletir o contrato escolhido.',
            style: TextStyle(
              fontSize: 13,
              color: Colors.black54,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          for (final c in contratos)
            _ContratoItem(
              contrato: c,
              selecionado: c.id == selecionadoId,
              onTap: () => Navigator.of(context).pop(c.id),
            ),
        ],
      ),
    );
  }
}

class _ContratoItem extends StatelessWidget {
  const _ContratoItem({
    required this.contrato,
    required this.selecionado,
    required this.onTap,
  });
  final ContratoResumoDto contrato;
  final bool selecionado;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selecionado
          ? BrandTokens.primary.withOpacity(0.10)
          : Colors.black.withOpacity(0.03),
      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
      child: InkWell(
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceMd,
            vertical: BrandTokens.spaceMd,
          ),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selecionado
                      ? BrandTokens.primary
                      : BrandTokens.primary.withOpacity(0.15),
                  borderRadius:
                      BorderRadius.circular(BrandTokens.radiusSm),
                ),
                child: Icon(
                  Icons.home_rounded,
                  color: selecionado ? Colors.white : BrandTokens.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: BrandTokens.spaceMd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      contrato.apelidoCurto,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: BrandTokens.primaryDark,
                      ),
                    ),
                    if (contrato.enderecoResumido.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        contrato.enderecoResumido,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.black54,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                    if (contrato.plano.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        contrato.plano,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: BrandTokens.primary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              if (selecionado)
                const Icon(
                  Icons.check_circle_rounded,
                  color: BrandTokens.primary,
                  size: 22,
                )
              else
                const SizedBox(width: 22),
            ],
          ),
        ),
      ),
    );
  }
}
