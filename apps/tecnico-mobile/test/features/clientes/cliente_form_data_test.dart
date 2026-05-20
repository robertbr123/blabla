import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/api/api_client.dart';
import 'package:tecnico_mobile/features/clientes/cliente_form_data.dart';

class _QueuedAdapter implements HttpClientAdapter {
  _QueuedAdapter(this._handlers);

  final List<ResponseBody Function(RequestOptions options)> _handlers;
  int _index = 0;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final handler = _handlers[_index++];
    return handler(options);
  }
}

ResponseBody _jsonBody(Object body, int statusCode) {
  return ResponseBody.fromString(
    jsonEncode(body),
    statusCode,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

void main() {
  test('planosProvider returns sgp plans when endpoint succeeds', () async {
    final dio = Dio()
      ..httpClientAdapter = _QueuedAdapter([
        (_) => _jsonBody({
              'provider': 'ondeline',
              'planos': [
                {
                  'id': 12,
                  'grupo': 'Fibra',
                  'descricao': '500 Mega',
                  'preco': 129.9,
                  'download': 512000,
                  'upload': 256000,
                },
              ],
            }, 200),
      ]);

    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWith((ref) => dio),
      ],
    );
    addTearDown(container.dispose);

    final planos = await container.read(planosProvider.future);

    expect(planos, hasLength(1));
    expect(planos.single.id, 12);
    expect(planos.single.descricao, '500 Mega');
    expect(planos.single.isFallback, isFalse);
  });

  test('planosProvider falls back to configured plans on sgp 502', () async {
    final dio = Dio()
      ..httpClientAdapter = _QueuedAdapter([
        (options) => _jsonBody(
              {'detail': 'SGP indisponivel'},
              502,
            ),
        (_) => _jsonBody([
              {
                'index': 3,
                'nome': 'Plano Backup',
                'preco': 99.9,
                'velocidade': '80MB',
              },
            ], 200),
      ]);

    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWith((ref) => dio),
      ],
    );
    addTearDown(container.dispose);

    final planos = await container.read(planosProvider.future);

    expect(planos, hasLength(1));
    expect(planos.single.isFallback, isTrue);
    expect(planos.single.id, 3);
    expect(planos.single.velocidadeStr(), '80MB');
  });
}
