import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import 'auth_storage.dart';

class AuthRepository {
  AuthRepository(this._dio);
  final Dio _dio;

  static const _base = '/api/v1/cliente-app/auth';

  Future<RegisterStartResult> registerStart(String cpf) async {
    try {
      final r = await _dio.post(
        '$_base/register/start',
        data: {'cpf': cpf},
        options: Options(extra: const {'skipAuth': true}),
      );
      return RegisterStartResult.ok(
          maskedPhone: r.data['masked_phone'] as String);
    } on DioException catch (e) {
      return RegisterStartResult.error(_messageFromDio(e));
    }
  }

  Future<RegisterVerifyResult> registerVerify(String cpf, String code) async {
    try {
      final r = await _dio.post(
        '$_base/register/verify',
        data: {'cpf': cpf, 'code': code},
        options: Options(extra: const {'skipAuth': true}),
      );
      return RegisterVerifyResult.ok(
          setupToken: r.data['setup_token'] as String);
    } on DioException catch (e) {
      return RegisterVerifyResult.error(_messageFromDio(e));
    }
  }

  Future<AuthResult> registerPassword({
    required String setupToken,
    required String password,
    required String cpfLast4,
    required String nome,
  }) async {
    try {
      final r = await _dio.post(
        '$_base/register/password',
        data: {'setup_token': setupToken, 'password': password},
        options: Options(extra: const {'skipAuth': true}),
      );
      final token = r.data['access_token'] as String;
      await writeAccessToken(token);
      await writeSession(
          cpfLast4: cpfLast4, nome: nome, biometricEnabled: false);
      return AuthResult.ok(accessToken: token);
    } on DioException catch (e) {
      return AuthResult.error(_messageFromDio(e));
    }
  }

  Future<AuthResult> login({
    required String cpf,
    required String password,
  }) async {
    try {
      final r = await _dio.post(
        '$_base/login',
        data: {'cpf': cpf, 'password': password},
        options: Options(extra: const {'skipAuth': true}),
      );
      final token = r.data['access_token'] as String;
      await writeAccessToken(token);
      final existingNome = (await readNome()) ?? '';
      final cpfDigits = cpf.replaceAll(RegExp(r'\D'), '');
      await writeSession(
        cpfLast4: cpfDigits.substring(cpfDigits.length - 4),
        nome: existingNome,
        biometricEnabled: await readBiometricEnabled(),
      );
      return AuthResult.ok(accessToken: token);
    } on DioException catch (e) {
      return AuthResult.error(_messageFromDio(e));
    }
  }

  Future<bool> forgot(String cpf) async {
    try {
      await _dio.post(
        '$_base/forgot',
        data: {'cpf': cpf},
        options: Options(extra: const {'skipAuth': true}),
      );
      return true;
    } on DioException {
      return false;
    }
  }

  Future<void> logout() => clearAuth();

  String _messageFromDio(DioException e) {
    final d = e.response?.data;
    if (d is Map && d['detail'] is String) return d['detail'] as String;
    final code = e.response?.statusCode;
    if (code == 404) return 'CPF nao encontrado';
    if (code == 409) return 'Ja existe cadastro pra esse CPF';
    if (code == 401) return 'Credenciais invalidas';
    if (code == 429) {
      return 'Muitas tentativas. Tente novamente em alguns minutos';
    }
    // Sem response — devolve causa especifica pra debugar.
    // Em prod (Fase 7) volta a ser generico.
    final type = e.type.name;
    final base = e.requestOptions.baseUrl;
    final path = e.requestOptions.path;
    final msg = e.message ?? e.error?.toString() ?? 'sem detalhe';
    return 'Falha [$type] $base$path: $msg';
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

sealed class RegisterStartResult {
  const RegisterStartResult();
  factory RegisterStartResult.ok({required String maskedPhone}) =
      RegisterStartOk;
  factory RegisterStartResult.error(String message) = RegisterStartError;
}

class RegisterStartOk extends RegisterStartResult {
  const RegisterStartOk({required this.maskedPhone});
  final String maskedPhone;
}

class RegisterStartError extends RegisterStartResult {
  const RegisterStartError(this.message);
  final String message;
}

sealed class RegisterVerifyResult {
  const RegisterVerifyResult();
  factory RegisterVerifyResult.ok({required String setupToken}) =
      RegisterVerifyOk;
  factory RegisterVerifyResult.error(String message) = RegisterVerifyError;
}

class RegisterVerifyOk extends RegisterVerifyResult {
  const RegisterVerifyOk({required this.setupToken});
  final String setupToken;
}

class RegisterVerifyError extends RegisterVerifyResult {
  const RegisterVerifyError(this.message);
  final String message;
}

sealed class AuthResult {
  const AuthResult();
  factory AuthResult.ok({required String accessToken}) = AuthOk;
  factory AuthResult.error(String message) = AuthError;
}

class AuthOk extends AuthResult {
  const AuthOk({required this.accessToken});
  final String accessToken;
}

class AuthError extends AuthResult {
  const AuthError(this.message);
  final String message;
}
