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
  test('CreateClienteCampoIn serializes optional email when present', () {
    final body = CreateClienteCampoIn(
      cpf: '12345678901',
      nome: 'Cliente Teste',
      dob: '2026-05-20',
      telefone: '92999998888',
      email: 'cliente@teste.com',
      cep: '69900000',
      address: 'Rua A',
      number: '12',
      complement: null,
      neighborhood: 'Centro',
      city: 'Rio Branco',
      state: 'AC',
      planId: 1,
      planNome: 'Plano X',
      pppoeUser: null,
      pppoePass: null,
      dueDate: 20,
      serial: null,
      contrato: null,
      observation: null,
      latitude: null,
      longitude: null,
      locationAccuracy: null,
      materiais: const [],
    );

    expect(body.toJson()['email'], 'cliente@teste.com');
    expect(body.toJson()['due_date'], 20);
  });

  test('extractDioMessage prefers backend detail', () {
    final error = DioException(
      requestOptions: RequestOptions(path: '/api/v1/clientes-campo/x/fotos'),
      response: Response(
        requestOptions: RequestOptions(path: '/api/v1/clientes-campo/x/fotos'),
        statusCode: 500,
        data: {'detail': 'arquivo da foto inválido'},
      ),
    );

    expect(
      extractDioMessage(error, fallback: 'fallback'),
      'arquivo da foto inválido',
    );
  });

  test('imageUploadFilename preserves the real file extension', () {
    expect(
      imageUploadFilename('/tmp/DCIM/IMG_1001.HEIC'),
      'IMG_1001.HEIC',
    );
    expect(
      imageUploadFilename(''),
      'foto.jpg',
    );
  });

  test('planosProvider retorna planos do blabla (/planos)', () async {
    // Cadastro usa os planos configurados no blabla (/api/v1/planos), não SGP.
    final dio = Dio()
      ..httpClientAdapter = _QueuedAdapter([
        (_) => _jsonBody([
              {
                'index': 3,
                'nome': 'Plano Fibra 500',
                'preco': 129.9,
                'velocidade': '500MB',
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
    expect(planos.single.id, 3);
    expect(planos.single.descricao, 'Plano Fibra 500');
    expect(planos.single.isFallback, isTrue);
    expect(planos.single.velocidadeStr(), '500MB');
  });

  test('planosProvider propaga erro quando /planos falha sem cache', () async {
    // Sem cache local (ambiente de teste não tem path_provider), erro de rede
    // no /planos deve propagar.
    final dio = Dio()
      ..httpClientAdapter = _QueuedAdapter([
        (_) => _jsonBody({'detail': 'erro'}, 502),
      ]);

    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWith((ref) => dio),
      ],
    );
    addTearDown(container.dispose);

    await expectLater(
      container.read(planosProvider.future),
      throwsA(isA<DioException>()),
    );
  });
}
