import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// ID do contrato atualmente selecionado pelo cliente.
///
/// Persiste em SharedPreferences pra sobreviver a restart do app.
/// Quando null → backend usa o default (primeiro ativo / primeiro qualquer).
class ContratoAtualNotifier extends StateNotifier<String?> {
  ContratoAtualNotifier() : super(null) {
    _hydrate();
  }

  static const _key = 'contrato_atual_id';

  Future<void> _hydrate() async {
    final p = await SharedPreferences.getInstance();
    state = p.getString(_key);
  }

  Future<void> selecionar(String? contratoId) async {
    state = contratoId;
    final p = await SharedPreferences.getInstance();
    if (contratoId == null) {
      await p.remove(_key);
    } else {
      await p.setString(_key, contratoId);
    }
  }

  Future<void> clear() async {
    state = null;
    final p = await SharedPreferences.getInstance();
    await p.remove(_key);
  }
}

final contratoAtualProvider =
    StateNotifierProvider<ContratoAtualNotifier, String?>(
  (ref) => ContratoAtualNotifier(),
);
