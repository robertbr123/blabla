import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_storage.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'https://apiblabla.robertbr.dev',
);

final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: apiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 30),
    headers: const {'Accept': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final skipAuth = options.extra['skipAuth'] == true;
      if (!skipAuth) {
        final token = await readAccessToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
      }
      handler.next(options);
    },
    onError: (e, handler) async {
      final code = e.response?.statusCode;
      final isAuthFlow =
          e.requestOptions.path.startsWith('/api/v1/cliente-app/auth/');
      if (code == 401 && !isAuthFlow) {
        await clearAuth();
      }
      handler.next(e);
    },
  ));

  return dio;
});
