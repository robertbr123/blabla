import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_storage.dart';

/// Notifier simples — bate em secure_storage para descobrir se ha sessao.
class AuthRefresh extends ChangeNotifier {
  void bump() => notifyListeners();
}

final authRefreshProvider = ChangeNotifierProvider<AuthRefresh>(
  (ref) => AuthRefresh(),
);

final hasTokenProvider = FutureProvider<bool>((ref) async {
  ref.watch(authRefreshProvider);
  final t = await readAccessToken();
  return t != null && t.isNotEmpty;
});

class SessionSnapshot {
  const SessionSnapshot({
    required this.cpfLast4,
    required this.nome,
    required this.biometricEnabled,
  });
  final String cpfLast4;
  final String nome;
  final bool biometricEnabled;
}

final sessionSnapshotProvider = FutureProvider<SessionSnapshot?>((ref) async {
  ref.watch(authRefreshProvider);
  final cpfLast4 = await readCpfLast4();
  if (cpfLast4 == null) return null;
  return SessionSnapshot(
    cpfLast4: cpfLast4,
    nome: (await readNome()) ?? '',
    biometricEnabled: await readBiometricEnabled(),
  );
});
