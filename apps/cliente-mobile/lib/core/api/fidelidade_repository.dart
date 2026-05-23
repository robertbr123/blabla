import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class FidelidadeBreakdownDto {
  FidelidadeBreakdownDto({
    required this.tempoCasaMeses,
    required this.tempoCasaPontos,
    required this.faturasPagasQtd,
    required this.faturasPagasPontos,
    this.missoesQtd = 0,
    this.missoesPontos = 0,
  });

  factory FidelidadeBreakdownDto.fromJson(Map<String, dynamic> j) =>
      FidelidadeBreakdownDto(
        tempoCasaMeses: j['tempo_casa_meses'] as int,
        tempoCasaPontos: j['tempo_casa_pontos'] as int,
        faturasPagasQtd: j['faturas_pagas_qtd'] as int,
        faturasPagasPontos: j['faturas_pagas_pontos'] as int,
        missoesQtd: (j['missoes_qtd'] as int?) ?? 0,
        missoesPontos: (j['missoes_pontos'] as int?) ?? 0,
      );

  final int tempoCasaMeses;
  final int tempoCasaPontos;
  final int faturasPagasQtd;
  final int faturasPagasPontos;
  final int missoesQtd;
  final int missoesPontos;
}

class RecompensaDto {
  RecompensaDto({
    required this.slug,
    required this.label,
    required this.pontos,
    required this.disponivel,
  });

  factory RecompensaDto.fromJson(Map<String, dynamic> j) => RecompensaDto(
        slug: j['slug'] as String,
        label: j['label'] as String,
        pontos: j['pontos'] as int,
        disponivel: j['disponivel'] as bool,
      );

  final String slug;
  final String label;
  final int pontos;
  final bool disponivel;
}

class ResgateDto {
  ResgateDto({
    required this.id,
    required this.recompensaSlug,
    required this.recompensaLabel,
    required this.pontosGastos,
    required this.status,
    this.obsAdmin,
    required this.criadoEm,
  });

  factory ResgateDto.fromJson(Map<String, dynamic> j) => ResgateDto(
        id: j['id'] as String,
        recompensaSlug: j['recompensa_slug'] as String,
        recompensaLabel: j['recompensa_label'] as String,
        pontosGastos: j['pontos_gastos'] as int,
        status: j['status'] as String,
        obsAdmin: j['obs_admin'] as String?,
        criadoEm: DateTime.parse(j['criado_em'] as String),
      );

  final String id;
  final String recompensaSlug;
  final String recompensaLabel;
  final int pontosGastos;
  final String status; // pendente|aprovado|aplicado|rejeitado
  final String? obsAdmin;
  final DateTime criadoEm;
}

class FidelidadeDto {
  FidelidadeDto({
    required this.pontosTotal,
    required this.pontosDisponiveis,
    required this.breakdown,
    required this.recompensas,
    required this.resgates,
  });

  factory FidelidadeDto.fromJson(Map<String, dynamic> j) => FidelidadeDto(
        pontosTotal: j['pontos_total'] as int,
        pontosDisponiveis: j['pontos_disponiveis'] as int,
        breakdown:
            FidelidadeBreakdownDto.fromJson(j['breakdown'] as Map<String, dynamic>),
        recompensas: ((j['recompensas'] as List?) ?? const [])
            .map((c) => RecompensaDto.fromJson(c as Map<String, dynamic>))
            .toList(),
        resgates: ((j['resgates'] as List?) ?? const [])
            .map((c) => ResgateDto.fromJson(c as Map<String, dynamic>))
            .toList(),
      );

  final int pontosTotal;
  final int pontosDisponiveis;
  final FidelidadeBreakdownDto breakdown;
  final List<RecompensaDto> recompensas;
  final List<ResgateDto> resgates;
}

class FidelidadeRepository {
  FidelidadeRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/fidelidade';

  Future<FidelidadeDto> get() async {
    final r = await _dio.get(_base);
    return FidelidadeDto.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> resgatar(String slug) async {
    await _dio.post('$_base/resgatar', data: {'recompensa_slug': slug});
  }
}

final fidelidadeRepositoryProvider = Provider<FidelidadeRepository>(
  (ref) => FidelidadeRepository(ref.watch(apiClientProvider)),
);

final fidelidadeProvider = FutureProvider<FidelidadeDto>(
  (ref) => ref.watch(fidelidadeRepositoryProvider).get(),
);
