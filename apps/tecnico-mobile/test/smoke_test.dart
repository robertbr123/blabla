import 'package:flutter_test/flutter_test.dart';

import 'package:tecnico_mobile/core/sync/outbox_kind.dart';

void main() {
  test('OutboxKindString parse roundtrip', () {
    for (final k in OutboxKind.values) {
      expect(OutboxKindString.parse(k.wire), k);
    }
  });

  test('OutboxKindString parse fallback', () {
    expect(OutboxKindString.parse('garbage'), OutboxKind.iniciar);
  });
}
