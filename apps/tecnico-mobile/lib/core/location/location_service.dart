import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

class LocationResult {
  final double lat;
  final double lng;
  final double? accuracyMeters;
  LocationResult(this.lat, this.lng, this.accuracyMeters);
}

abstract class LocationService {
  /// Captura uma posicao atual com permissoes. Retorna null se usuario negar
  /// ou GPS estiver desligado. Timeout 8s.
  Future<LocationResult?> capture();
}

final locationServiceProvider = Provider<LocationService>(
  (ref) => DeviceLocationService(),
);

class DeviceLocationService implements LocationService {
  DeviceLocationService({GeolocatorFacade? geolocator})
      : _geolocator = geolocator ?? const GeolocatorFacade();

  final GeolocatorFacade _geolocator;

  @override
  Future<LocationResult?> capture() async {
    final enabled = await _geolocator.isLocationServiceEnabled();
    if (!enabled) return null;

    var permission = await _geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await _geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return null;
    }

    try {
      final pos = await _geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      return LocationResult(pos.latitude, pos.longitude, pos.accuracy);
    } catch (_) {
      // Tenta last-known se a leitura ao vivo falhou (timeout, sem fix).
      final last = await _geolocator.getLastKnownPosition();
      if (last == null) return null;
      return LocationResult(last.latitude, last.longitude, last.accuracy);
    }
  }
}

class GeolocatorFacade {
  const GeolocatorFacade();

  Future<bool> isLocationServiceEnabled() {
    return Geolocator.isLocationServiceEnabled();
  }

  Future<LocationPermission> checkPermission() {
    return Geolocator.checkPermission();
  }

  Future<LocationPermission> requestPermission() {
    return Geolocator.requestPermission();
  }

  Future<Position> getCurrentPosition({
    required LocationSettings locationSettings,
  }) {
    return Geolocator.getCurrentPosition(locationSettings: locationSettings);
  }

  Future<Position?> getLastKnownPosition() {
    return Geolocator.getLastKnownPosition();
  }
}
