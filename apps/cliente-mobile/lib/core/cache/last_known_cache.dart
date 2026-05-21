import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../api/dto.dart';

class LastKnownCache {
  static const _kMe = 'last_me_json';
  static const _kPlano = 'last_plano_json';

  Future<void> writeMe(MeDto me) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kMe, jsonEncode(me.toJson()));
  }

  Future<MeDto?> readMe() async {
    final p = await SharedPreferences.getInstance();
    final s = p.getString(_kMe);
    if (s == null) return null;
    return MeDto.fromJson(jsonDecode(s) as Map<String, dynamic>);
  }

  Future<void> writePlano(PlanoDto plano) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kPlano, jsonEncode(plano.toJson()));
  }

  Future<PlanoDto?> readPlano() async {
    final p = await SharedPreferences.getInstance();
    final s = p.getString(_kPlano);
    if (s == null) return null;
    return PlanoDto.fromJson(jsonDecode(s) as Map<String, dynamic>);
  }

  Future<void> clear() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_kMe);
    await p.remove(_kPlano);
  }
}
