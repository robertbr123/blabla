import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_storage.dart';
import 'session_state.dart';

class AuthRefreshListenable extends ChangeNotifier {
  void markChanged() {
    notifyListeners();
  }
}

final authRefreshListenableProvider = Provider<AuthRefreshListenable>((ref) {
  final listenable = AuthRefreshListenable();
  ref.onDispose(listenable.dispose);
  return listenable;
});

final hasTokenProvider = FutureProvider<bool>((ref) async {
  final token = await readAccessToken();
  return token != null && token.isNotEmpty;
});

final sessionSnapshotProvider = FutureProvider<SessionSnapshot?>((ref) async {
  return readSessionSnapshot();
});
