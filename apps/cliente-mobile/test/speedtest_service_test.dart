import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/features/conexao/speedtest_service.dart';

void main() {
  group('mbpsFrom', () {
    test('converte bytes + duração em Mbps', () {
      // 1.000.000 bytes em 1s => 8 Mbit em 1s => 8 Mbps
      final mbps = mbpsFrom(1000000, const Duration(seconds: 1));
      expect(mbps, closeTo(8.0, 0.001));
    });

    test('meio segundo dobra a taxa', () {
      final mbps = mbpsFrom(1000000, const Duration(milliseconds: 500));
      expect(mbps, closeTo(16.0, 0.001));
    });

    test('duração zero não explode (retorna 0)', () {
      final mbps = mbpsFrom(1000000, Duration.zero);
      expect(mbps, 0.0);
    });

    test('zero bytes retorna 0 mbps', () {
      final mbps = mbpsFrom(0, const Duration(seconds: 1));
      expect(mbps, 0.0);
    });
  });

  group('medianMs', () {
    test('lista ímpar retorna o valor central', () {
      expect(medianMs([10, 30, 20]), 20);
    });

    test('lista par retorna a média dos dois centrais', () {
      expect(medianMs([10, 20, 30, 40]), 25);
    });

    test('lista de um elemento retorna o próprio elemento', () {
      expect(medianMs([42]), 42);
    });

    test('lista vazia retorna 0', () {
      expect(medianMs([]), 0);
    });

    test('não é afetada pela ordem de entrada', () {
      expect(medianMs([30, 10, 20]), 20);
    });
  });
}
