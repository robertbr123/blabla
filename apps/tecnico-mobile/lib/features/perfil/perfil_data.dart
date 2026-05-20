import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_storage.dart';
import '../../core/db/database.dart';
import '../../core/db/perfil_repo.dart';

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
        estatisticas: PerfilEstatisticas.fromJson(
            j['estatisticas'] as Map<String, dynamic>),
      );
}

final perfilLocalRepoProvider = Provider<PerfilLocalRepo>((ref) {
  return PerfilLocalRepo(ref.watch(dbProvider));
});

final perfilReadUserIdProvider = Provider<Future<String?> Function()>((ref) {
  return readUserId;
});

final perfilProvider = FutureProvider<Perfil>((ref) async {
  final repo = ref.watch(perfilLocalRepoProvider);
  final readCurrentUserId = ref.watch(perfilReadUserIdProvider);
  final userId = await readCurrentUserId();
  final cached = await _loadCachedPerfil(repo: repo, userId: userId);

  try {
    final dio = ref.watch(apiClientProvider);
    final r = await dio.get('/api/v1/tecnico/me/perfil');
    final raw = (r.data as Map).cast<String, dynamic>();
    if (userId != null && userId.isNotEmpty) {
      final normalized = _normalizePerfilPayload(raw, userId);
      await repo.save(normalized);
      return Perfil.fromJson(normalized);
    }
    return Perfil.fromJson(raw);
  } on DioException catch (e) {
    if (_shouldUseCachedSnapshot(e) && cached != null) {
      return Perfil.fromJson(cached);
    }
    throw e;
  }
});

Future<Map<String, dynamic>?> _loadCachedPerfil({
  required PerfilLocalRepo repo,
  required String? userId,
}) {
  if (userId == null || userId.isEmpty) {
    return Future.value(null);
  }
  return repo.get(userId: userId);
}

bool _shouldUseCachedSnapshot(DioException error) {
  return error.type == DioExceptionType.connectionError ||
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.sendTimeout ||
      error.type == DioExceptionType.receiveTimeout;
}

Map<String, dynamic> _normalizePerfilPayload(
  Map<String, dynamic> payload,
  String userId,
) {
  return <String, dynamic>{...payload, 'user_id': userId};
}

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
      options: Options(
        extra: {'skipSessionExpiryHandling': true},
      ),
    );
  }
}

final perfilActionsProvider = Provider<PerfilActions>((ref) {
  return PerfilActions(ref.watch(apiClientProvider));
});
