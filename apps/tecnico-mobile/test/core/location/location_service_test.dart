import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:tecnico_mobile/core/location/location_service.dart';

class _FakeGeolocatorFacade extends GeolocatorFacade {
  _FakeGeolocatorFacade({
    required this.serviceEnabled,
    required this.initialPermission,
    this.requestedPermission,
    this.currentPosition,
    this.lastKnownPosition,
    this.throwOnCurrentPosition = false,
  });

  final bool serviceEnabled;
  final LocationPermission initialPermission;
  final LocationPermission? requestedPermission;
  final Position? currentPosition;
  final Position? lastKnownPosition;
  final bool throwOnCurrentPosition;

  @override
  Future<bool> isLocationServiceEnabled() async => serviceEnabled;

  @override
  Future<LocationPermission> checkPermission() async => initialPermission;

  @override
  Future<LocationPermission> requestPermission() async {
    return requestedPermission ?? initialPermission;
  }

  @override
  Future<Position> getCurrentPosition({
    required LocationSettings locationSettings,
  }) async {
    if (throwOnCurrentPosition || currentPosition == null) {
      throw Exception('no-fix');
    }
    return currentPosition!;
  }

  @override
  Future<Position?> getLastKnownPosition() async => lastKnownPosition;
}

Position _position({
  required double lat,
  required double lng,
  double accuracy = 12,
}) {
  return Position(
    longitude: lng,
    latitude: lat,
    timestamp: DateTime(2026, 5, 20, 12),
    accuracy: accuracy,
    altitude: 0,
    altitudeAccuracy: 0,
    heading: 0,
    headingAccuracy: 0,
    speed: 0,
    speedAccuracy: 0,
  );
}

void main() {
  test('capture requests permission and returns current location on success',
      () async {
    final service = DeviceLocationService(
      geolocator: _FakeGeolocatorFacade(
        serviceEnabled: true,
        initialPermission: LocationPermission.denied,
        requestedPermission: LocationPermission.whileInUse,
        currentPosition: _position(lat: -3.1, lng: -60.0),
      ),
    );

    final result = await service.capture();

    expect(result, isNotNull);
    expect(result!.lat, -3.1);
    expect(result.lng, -60.0);
  });

  test('capture returns null when location service is disabled', () async {
    final service = DeviceLocationService(
      geolocator: _FakeGeolocatorFacade(
        serviceEnabled: false,
        initialPermission: LocationPermission.whileInUse,
      ),
    );

    final result = await service.capture();

    expect(result, isNull);
  });

  test('capture falls back to last known position when live fix fails',
      () async {
    final service = DeviceLocationService(
      geolocator: _FakeGeolocatorFacade(
        serviceEnabled: true,
        initialPermission: LocationPermission.always,
        throwOnCurrentPosition: true,
        lastKnownPosition: _position(lat: -3.11, lng: -60.01, accuracy: 40),
      ),
    );

    final result = await service.capture();

    expect(result, isNotNull);
    expect(result!.lat, -3.11);
    expect(result.lng, -60.01);
    expect(result.accuracyMeters, 40);
  });
}
