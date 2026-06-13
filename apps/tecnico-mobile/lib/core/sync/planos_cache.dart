import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

Future<File> _planosCacheFile() async {
  final dir = await getApplicationDocumentsDirectory();
  return File(p.join(dir.path, 'planos_cache.json'));
}

/// Salva o JSON cru da resposta de /api/v1/planos (lista de planos do blabla).
Future<void> writePlanosCache(Object? raw) async {
  try {
    await (await _planosCacheFile()).writeAsString(jsonEncode(raw));
  } catch (_) {/* best-effort */}
}

/// Lê o JSON cru cacheado dos planos do blabla (lista) ou null.
Future<Object?> readPlanosCache() async {
  try {
    final f = await _planosCacheFile();
    if (!await f.exists()) return null;
    return jsonDecode(await f.readAsString());
  } catch (_) {
    return null;
  }
}
