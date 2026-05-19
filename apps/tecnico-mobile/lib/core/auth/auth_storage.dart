import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'session_state.dart';

const _kAccess = 'access_token';
const _kUserId = 'user_id';
const _kRole = 'role';
const _kSessionUserId = 'session_user_id';
const _kSessionRole = 'session_role';
const _kSessionNome = 'session_nome';
const _kSessionBiometricEnabled = 'session_biometric_enabled';

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
  await _storage.delete(key: _kSessionUserId);
  await _storage.delete(key: _kSessionRole);
  await _storage.delete(key: _kSessionNome);
  await _storage.delete(key: _kSessionBiometricEnabled);
}

Future<void> writeUser({required String userId, required String role}) async {
  await _storage.write(key: _kUserId, value: userId);
  await _storage.write(key: _kRole, value: role);
}

Future<String?> readUserId() => _storage.read(key: _kUserId);
Future<String?> readRole() => _storage.read(key: _kRole);

Future<void> saveSessionSnapshot({
  required String userId,
  required String role,
  required String nome,
  required bool biometricEnabled,
}) async {
  await _storage.write(key: _kSessionUserId, value: userId);
  await _storage.write(key: _kSessionRole, value: role);
  await _storage.write(key: _kSessionNome, value: nome);
  await _storage.write(
    key: _kSessionBiometricEnabled,
    value: biometricEnabled ? '1' : '0',
  );
}

Future<SessionSnapshot?> readSessionSnapshot() async {
  final userId = await _storage.read(key: _kSessionUserId);
  final role = await _storage.read(key: _kSessionRole);
  final nome = await _storage.read(key: _kSessionNome);
  final biometricValue = await _storage.read(key: _kSessionBiometricEnabled);

  if (userId == null ||
      role == null ||
      nome == null ||
      biometricValue == null) {
    return null;
  }

  return SessionSnapshot(
    userId: userId,
    role: role,
    nome: nome,
    biometricEnabled: biometricValue == '1',
  );
}
