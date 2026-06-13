import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Rascunho de cadastro de cliente salvo localmente (offline). Só payload —
/// o cadastro não tem fotos no fluxo (fotos são anexadas no detalhe, online).
class CadastroDraft {
  final String id;
  final DateTime createdAt;
  final String cpf;
  final String nome;
  final Map<String, dynamic> payload;

  CadastroDraft({
    required this.id,
    required this.createdAt,
    required this.cpf,
    required this.nome,
    required this.payload,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'created_at': createdAt.toIso8601String(),
        'cpf': cpf,
        'nome': nome,
        'payload': payload,
      };

  factory CadastroDraft.fromJson(Map<String, dynamic> j) => CadastroDraft(
        id: j['id'] as String,
        createdAt:
            DateTime.tryParse(j['created_at'] as String? ?? '') ?? DateTime.now(),
        cpf: (j['cpf'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        payload: (j['payload'] as Map).cast<String, dynamic>(),
      );
}

class CadastroDraftRepo {
  Future<Directory> _dir() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(docs.path, 'cadastro_drafts'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<CadastroDraft> save({
    required Map<String, dynamic> payload,
    required String cpf,
    required String nome,
  }) async {
    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final draft = CadastroDraft(
      id: id,
      createdAt: DateTime.now(),
      cpf: cpf,
      nome: nome,
      payload: payload,
    );
    final dir = await _dir();
    await File(p.join(dir.path, '$id.json'))
        .writeAsString(jsonEncode(draft.toJson()));
    return draft;
  }

  Future<List<CadastroDraft>> list() async {
    final dir = await _dir();
    final entries = await dir.list().toList();
    final drafts = <CadastroDraft>[];
    for (final e in entries) {
      if (e is! File || !e.path.endsWith('.json')) continue;
      try {
        drafts.add(CadastroDraft.fromJson(
            (jsonDecode(await e.readAsString()) as Map).cast<String, dynamic>()));
      } catch (_) {/* ignora arquivo corrompido */}
    }
    drafts.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return drafts;
  }

  Future<void> delete(String id) async {
    final f = File(p.join((await _dir()).path, '$id.json'));
    if (await f.exists()) await f.delete();
  }
}

final cadastroDraftRepoProvider =
    Provider<CadastroDraftRepo>((ref) => CadastroDraftRepo());

final cadastroDraftsProvider = FutureProvider<List<CadastroDraft>>(
  (ref) => ref.watch(cadastroDraftRepoProvider).list(),
);
