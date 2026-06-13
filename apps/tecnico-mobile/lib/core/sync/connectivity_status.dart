import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Online (true) / offline (false) pela interface de rede. Dica de UI —
/// não garante internet real (o fallback cache-first é a verdade).
final connectivityStatusProvider = StreamProvider<bool>((ref) async* {
  bool online(List<ConnectivityResult> r) =>
      r.any((c) => c != ConnectivityResult.none);
  yield online(await Connectivity().checkConnectivity());
  yield* Connectivity().onConnectivityChanged.map(online);
});
