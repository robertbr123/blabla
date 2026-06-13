import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

Future<File> _planosCacheFile() async {
  final dir = await getApplicationDocumentsDirectory();
  return File(p.join(dir.path, 'planos_cache.json'));
}

/// Salva o JSON cru da resposta de /sgp/planos (shape {planos:[...]}).
Future<void> writePlanosCache(Object? raw) async {
  try {
    await (await _planosCacheFile()).writeAsString(jsonEncode(raw));
  } catch (_) {/* best-effort */}
}

/// Lê o JSON cru cacheado (mesmo shape de /sgp/planos) ou null.
Future<Map<String, dynamic>?> readPlanosCache() async {
  try {
    final f = await _planosCacheFile();
    if (!await f.exists()) return null;
    return (jsonDecode(await f.readAsString()) as Map).cast<String, dynamic>();
  } catch (_) {
    return null;
  }
}
