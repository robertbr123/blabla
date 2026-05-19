import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tecnico_mobile/core/auth/auth_storage.dart';

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('session snapshot stores display name and biometric eligibility',
      () async {
    await saveSessionSnapshot(
      userId: 'u1',
      role: 'tecnico',
      nome: 'Roberto',
      biometricEnabled: true,
    );

    final session = await readSessionSnapshot();
    expect(session?.userId, 'u1');
    expect(session?.role, 'tecnico');
    expect(session?.nome, 'Roberto');
    expect(session?.biometricEnabled, isTrue);
  });

  test('clearAuth removes saved session snapshot', () async {
    await saveSessionSnapshot(
      userId: 'u1',
      role: 'tecnico',
      nome: 'Roberto',
      biometricEnabled: true,
    );

    await clearAuth();

    expect(await readSessionSnapshot(), isNull);
  });

  test('session snapshot is invalid when biometric flag is missing', () async {
    await writeUser(userId: 'u1', role: 'tecnico');

    expect(await readSessionSnapshot(), isNull);
  });

  test('session snapshot does not mix with auth user keys', () async {
    await saveSessionSnapshot(
      userId: 'u1',
      role: 'tecnico',
      nome: 'Roberto',
      biometricEnabled: true,
    );

    await writeUser(userId: 'u2', role: 'admin');

    final session = await readSessionSnapshot();
    expect(session?.userId, 'u1');
    expect(session?.role, 'tecnico');
    expect(session?.nome, 'Roberto');
    expect(session?.biometricEnabled, isTrue);
  });
}
