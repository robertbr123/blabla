import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';

class PerfilEstatisticas {
  final int osPendentes;
  final int osEmAndamento;
  final int osConcluidasMes;
  final double? csatAvgMes;
  PerfilEstatisticas({
    required this.osPendentes,
    required this.osEmAndamento,
    required this.osConcluidasMes,
    required this.csatAvgMes,
  });
  factory PerfilEstatisticas.fromJson(Map<String, dynamic> j) =>
      PerfilEstatisticas(
        osPendentes: (j['os_pendentes'] ?? 0) as int,
        osEmAndamento: (j['os_em_andamento'] ?? 0) as int,
        osConcluidasMes: (j['os_concluidas_mes'] ?? 0) as int,
        csatAvgMes: (j['csat_avg_mes'] as num?)?.toDouble(),
      );
}

class Perfil {
  final String userId;
  final String email;
  final String nome;
  final String? whatsapp;
  final String role;
  final String? fotoB64;
  final bool ativo;
  final String? lastGpsTs;
  final PerfilEstatisticas estatisticas;

  Perfil({
    required this.userId,
    required this.email,
    required this.nome,
    required this.whatsapp,
    required this.role,
    required this.fotoB64,
    required this.ativo,
    required this.lastGpsTs,
    required this.estatisticas,
  });

  factory Perfil.fromJson(Map<String, dynamic> j) => Perfil(
        userId: (j['user_id'] ?? '') as String,
        email: (j['email'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        whatsapp: j['whatsapp'] as String?,
        role: (j['role'] ?? '') as String,
        fotoB64: j['foto_b64'] as String?,
        ativo: (j['ativo'] ?? true) as bool,
        lastGpsTs: j['last_gps_ts'] as String?,
        estatisticas:
            PerfilEstatisticas.fromJson(j['estatisticas'] as Map<String, dynamic>),
      );
}

final perfilProvider = FutureProvider<Perfil>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final r = await dio.get('/api/v1/tecnico/me/perfil');
  return Perfil.fromJson(r.data as Map<String, dynamic>);
});

class PerfilActions {
  final Dio _dio;
  PerfilActions(this._dio);

  Future<void> uploadFoto(String filePath) async {
    final form = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: 'avatar.jpg'),
    });
    await _dio.post('/api/v1/tecnico/me/foto', data: form);
  }

  Future<void> removerFoto() async {
    await _dio.delete('/api/v1/tecnico/me/foto');
  }

  Future<void> mudarSenha({
    required String atual,
    required String nova,
  }) async {
    await _dio.post(
      '/api/v1/tecnico/me/senha',
      data: {'senha_atual': atual, 'senha_nova': nova},
    );
  }
}

final perfilActionsProvider = Provider<PerfilActions>((ref) {
  return PerfilActions(ref.watch(apiClientProvider));
});
