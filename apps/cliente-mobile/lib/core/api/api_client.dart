import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../auth/auth_storage.dart';
import '../dev/dev_mode.dart';

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
      // Modo dev — intercepta antes de qualquer rede e devolve mock
      final p = await SharedPreferences.getInstance();
      if (p.getBool('dev_mode') == true) {
        final method = options.method.toUpperCase();
        final mock = mockResponse(method, options.path);
        if (mock != null) {
          return handler.resolve(
            Response(
              requestOptions: options,
              statusCode: method == 'POST' ? 201 : 200,
              data: mock,
            ),
          );
        }
      }

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
