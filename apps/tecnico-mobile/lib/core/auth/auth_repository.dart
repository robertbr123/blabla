import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import 'auth_storage.dart';
import 'session_state.dart';

class LoginResult {
  final String accessToken;
  final String userId;
  final String role;

  LoginResult({
    required this.accessToken,
    required this.userId,
    required this.role,
  });

  factory LoginResult.fromJson(Map<String, dynamic> j) => LoginResult(
        accessToken: j['access_token'] as String,
        userId: j['user_id'] as String,
        role: j['role'] as String,
      );
}

class AuthRepository {
  final Dio _dio;
  AuthRepository(this._dio);

  Future<LoginResult> login(String email, String password) async {
    final r = await _dio.post(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    final result = LoginResult.fromJson(r.data as Map<String, dynamic>);
    await writeAccessToken(result.accessToken);
    await writeUser(userId: result.userId, role: result.role);
    return result;
  }

  Future<void> logout() async {
    try {
      await _dio.post('/auth/logout');
    } catch (_) {
      // best-effort — limpa local seja como for
    }
    await clearAuth();
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

/// `true` se houver token salvo. Não valida o token contra o servidor —
/// o primeiro 401 já provoca redirect pra login.
final hasTokenProvider = FutureProvider<bool>((ref) async {
  final t = await readAccessToken();
  return t != null && t.isNotEmpty;
});

final sessionSnapshotProvider = FutureProvider<SessionSnapshot?>((ref) async {
  return readSessionSnapshot();
});
