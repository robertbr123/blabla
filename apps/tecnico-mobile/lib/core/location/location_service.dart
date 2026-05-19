import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

class LocationResult {
  final double lat;
  final double lng;
  final double? accuracyMeters;
  LocationResult(this.lat, this.lng, this.accuracyMeters);
}

class LocationService {
  /// Captura uma posicao atual com permissoes. Retorna null se usuario negar
  /// ou GPS estiver desligado. Timeout 8s.
  Future<LocationResult?> capture() async {
    final status = await Permission.location.request();
    if (!status.isGranted) return null;
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) return null;
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      return LocationResult(pos.latitude, pos.longitude, pos.accuracy);
    } catch (_) {
      // Tenta last-known se a leitura ao vivo falhou (timeout, sem fix).
      final last = await Geolocator.getLastKnownPosition();
      if (last == null) return null;
      return LocationResult(last.latitude, last.longitude, last.accuracy);
    }
  }
}
