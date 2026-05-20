import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/auth/auth_repository.dart';
import 'package:tecnico_mobile/core/auth/auth_storage.dart';

class _StaticResponseAdapter implements HttpClientAdapter {
  _StaticResponseAdapter(this.payload);

  final Map<String, dynamic> payload;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      '{"access_token":"${payload['access_token']}","user_id":"${payload['user_id']}","role":"${payload['role']}","nome":"${payload['nome']}"}',
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('login stores token and user data from api payload', () async {
    final dio = Dio();
    dio.httpClientAdapter = _StaticResponseAdapter({
      'access_token': 'token-1',
      'user_id': 'u1',
      'role': 'tecnico',
      'nome': 'Roberto',
    });

    final repo = AuthRepository(dio);
    await repo.login('roberto@empresa.com', '123456');

    expect(await readAccessToken(), 'token-1');
    expect(await readUserId(), 'u1');
    expect(await readRole(), 'tecnico');
    expect(await readSessionSnapshot(), isNull);
  });

  test('resolveLoginDisplayName prefers nome from api payload', () {
    final name = resolveLoginDisplayName(
      email: 'roberto@empresa.com',
      loginResult: LoginResult(
        accessToken: 'token-1',
        userId: 'u1',
        role: 'tecnico',
        nome: 'Roberto',
      ),
    );

    expect(name, 'Roberto');
  });

  test('resolveLoginDisplayName falls back to formatted email local part', () {
    final name = resolveLoginDisplayName(
      email: 'roberto.albino@empresa.com',
      loginResult: LoginResult(
        accessToken: 'token-1',
        userId: 'u1',
        role: 'tecnico',
        nome: null,
      ),
    );

    expect(name, 'Roberto Albino');
  });
}
