import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/ui/formatters.dart';

void main() {
  test('saudacao por faixa de horario', () {
    expect(saudacao(DateTime(2026, 1, 1, 5)), 'Bom dia,');
    expect(saudacao(DateTime(2026, 1, 1, 11, 59)), 'Bom dia,');
    expect(saudacao(DateTime(2026, 1, 1, 12)), 'Boa tarde,');
    expect(saudacao(DateTime(2026, 1, 1, 17, 59)), 'Boa tarde,');
    expect(saudacao(DateTime(2026, 1, 1, 18)), 'Boa noite,');
    expect(saudacao(DateTime(2026, 1, 1, 4, 59)), 'Boa noite,');
  });
}
