import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../db/database.dart';
import '../sync/outbox_repo.dart';
import 'auth_state.dart';
import 'auth_storage.dart';

class SessionCleanup {
  SessionCleanup(this._ref);

  final Ref _ref;
  bool _clearing = false;

  Future<void> clearLocalSession() async {
    if (_clearing) return;
    _clearing = true;
    try {
      await clearAuth();
      await OutboxRepo(_ref.read(dbProvider)).clear();
      final db = _ref.read(dbProvider);
      await db.transaction(() async {
        await db.delete(db.osLocal).go();
        await db.delete(db.estoqueLocal).go();
        await db.delete(db.perfilLocal).go();
        await db.delete(db.clienteCadastroLocal).go();
      });
      _ref.invalidate(hasTokenProvider);
      _ref.invalidate(sessionSnapshotProvider);
      _ref.read(authRefreshListenableProvider).markChanged();
    } finally {
      _clearing = false;
    }
  }
}

final sessionCleanupProvider = Provider<SessionCleanup>((ref) {
  return SessionCleanup(ref);
});
