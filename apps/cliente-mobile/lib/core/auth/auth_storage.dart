import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kAccess = 'cliente_access_token';
const _kCpfLast4 = 'cliente_cpf_last4';
const _kNome = 'cliente_nome';
const _kBiometric = 'cliente_biometric_enabled';

const _storage = FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

Future<String?> readAccessToken() => _storage.read(key: _kAccess);
Future<void> writeAccessToken(String token) =>
    _storage.write(key: _kAccess, value: token);

Future<void> writeSession({
  required String cpfLast4,
  required String nome,
  required bool biometricEnabled,
}) async {
  await _storage.write(key: _kCpfLast4, value: cpfLast4);
  await _storage.write(key: _kNome, value: nome);
  await _storage.write(key: _kBiometric, value: biometricEnabled.toString());
}

Future<String?> readCpfLast4() => _storage.read(key: _kCpfLast4);
Future<String?> readNome() => _storage.read(key: _kNome);
Future<bool> readBiometricEnabled() async {
  final v = await _storage.read(key: _kBiometric);
  return v == 'true';
}

Future<void> writeBiometricEnabled(bool enabled) =>
    _storage.write(key: _kBiometric, value: enabled.toString());

Future<void> clearAuth() async {
  await _storage.delete(key: _kAccess);
  await _storage.delete(key: _kCpfLast4);
  await _storage.delete(key: _kNome);
  await _storage.delete(key: _kBiometric);
}
