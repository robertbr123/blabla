import 'package:flutter_test/flutter_test.dart';
import 'package:local_auth_platform_interface/local_auth_platform_interface.dart';
import 'package:tecnico_mobile/core/auth/biometric_service.dart';

class _FakeLocalAuthPlatform extends LocalAuthPlatform {
  _FakeLocalAuthPlatform({
    required this.supportsBiometrics,
    required this.supportsDevice,
  });

  final bool supportsBiometrics;
  final bool supportsDevice;
  final bool authenticateResult = true;

  String? lastLocalizedReason;
  AuthenticationOptions? lastOptions;

  @override
  Future<bool> authenticate({
    required String localizedReason,
    required Iterable<AuthMessages> authMessages,
    AuthenticationOptions options = const AuthenticationOptions(),
  }) async {
    lastLocalizedReason = localizedReason;
    lastOptions = options;
    return authenticateResult;
  }

  @override
  Future<bool> deviceSupportsBiometrics() async => supportsBiometrics;

  @override
  Future<List<BiometricType>> getEnrolledBiometrics() async =>
      const <BiometricType>[];

  @override
  Future<bool> isDeviceSupported() async => supportsDevice;

  @override
  Future<bool> stopAuthentication() async => true;
}

void main() {
  late LocalAuthPlatform originalPlatform;

  setUpAll(() {
    originalPlatform = LocalAuthPlatform.instance;
  });

  tearDown(() {
    LocalAuthPlatform.instance = originalPlatform;
  });

  test('biometric service reports unsupported when no hardware', () async {
    LocalAuthPlatform.instance = _FakeLocalAuthPlatform(
      supportsBiometrics: false,
      supportsDevice: false,
    );

    final service = BiometricService();

    expect(await service.canUseBiometrics(), isFalse);
  });

  test('biometric service requires both support checks to pass', () async {
    LocalAuthPlatform.instance = _FakeLocalAuthPlatform(
      supportsBiometrics: true,
      supportsDevice: true,
    );
    final supportedService = BiometricService();
    expect(await supportedService.canUseBiometrics(), isTrue);

    LocalAuthPlatform.instance = _FakeLocalAuthPlatform(
      supportsBiometrics: true,
      supportsDevice: false,
    );
    final unsupportedService = BiometricService();
    expect(await unsupportedService.canUseBiometrics(), isFalse);
  });

  test('biometric service authenticates with biometric-only options', () async {
    final fake = _FakeLocalAuthPlatform(
      supportsBiometrics: true,
      supportsDevice: true,
    );
    LocalAuthPlatform.instance = fake;

    final service = BiometricService();
    final authenticated = await service.authenticate();

    expect(authenticated, isTrue);
    expect(fake.lastLocalizedReason, 'Entrar com Face ID');
    expect(fake.lastOptions?.biometricOnly, isTrue);
    expect(fake.lastOptions?.stickyAuth, isTrue);
  });
}
