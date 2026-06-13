import 'dart:async';

import 'package:google_fonts/google_fonts.dart';

/// Config global de testes: o google_fonts tenta baixar a fonte Inter da rede
/// na primeira vez que é usada. Em CI (sem rede) isso falha "after test
/// completion". Desligamos o fetch em runtime — os testes só validam tamanho,
/// peso e cor, que independem do arquivo da fonte.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  GoogleFonts.config.allowRuntimeFetching = false;
  await testMain();
}
