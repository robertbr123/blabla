import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kAccess = 'access_token';
const _kUserId = 'user_id';
const _kRole = 'role';

final _storage = const FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

Future<String?> readAccessToken() => _storage.read(key: _kAccess);

Future<void> writeAccessToken(String token) =>
    _storage.write(key: _kAccess, value: token);

Future<void> clearAuth() async {
  await _storage.delete(key: _kAccess);
  await _storage.delete(key: _kUserId);
  await _storage.delete(key: _kRole);
}

Future<void> writeUser({required String userId, required String role}) async {
  await _storage.write(key: _kUserId, value: userId);
  await _storage.write(key: _kRole, value: role);
}

Future<String?> readUserId() => _storage.read(key: _kUserId);
Future<String?> readRole() => _storage.read(key: _kRole);
