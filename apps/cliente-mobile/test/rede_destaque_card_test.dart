import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cliente_mobile/core/api/rede_repository.dart';
import 'package:cliente_mobile/features/home/widgets/rede_destaque_card.dart';

void main() {
  Widget wrap(List<Override> overrides) => ProviderScope(
        overrides: overrides,
        child: const MaterialApp(home: Scaffold(body: RedeDestaqueCard())),
      );

  RedeAparelhosDto dto({
    required bool encontrada,
    int total = 0,
    String saude = 'indisponivel',
  }) =>
      RedeAparelhosDto(
        encontrada: encontrada,
        total: total,
        aparelhos: const [],
        saude: saude,
      );

  testWidgets('some quando nao ha ONU mapeada (encontrada false)',
      (tester) async {
    await tester.pumpWidget(wrap([
      redeAparelhosProvider.overrideWith((ref) async => dto(encontrada: false)),
    ]));
    await tester.pumpAndSettle();
    expect(find.text('Minha Rede'), findsNothing);
  });

  testWidgets('some no erro (GenieACS fora / rede)', (tester) async {
    await tester.pumpWidget(wrap([
      redeAparelhosProvider.overrideWith((ref) async => throw Exception('boom')),
    ]));
    await tester.pumpAndSettle();
    expect(find.text('Minha Rede'), findsNothing);
  });

  testWidgets('mostra total e atalho de trocar senha quando ha ONU',
      (tester) async {
    await tester.pumpWidget(wrap([
      redeAparelhosProvider
          .overrideWith((ref) async => dto(encontrada: true, total: 8, saude: 'excelente')),
    ]));
    await tester.pumpAndSettle();
    expect(find.text('Minha Rede'), findsOneWidget);
    expect(find.textContaining('8'), findsOneWidget);
    expect(find.text('Trocar senha do WiFi'), findsOneWidget);
  });

  testWidgets('singular: 1 aparelho conectado', (tester) async {
    await tester.pumpWidget(wrap([
      redeAparelhosProvider
          .overrideWith((ref) async => dto(encontrada: true, total: 1, saude: 'boa')),
    ]));
    await tester.pumpAndSettle();
    expect(find.textContaining('aparelho conectado'), findsOneWidget);
  });

  testWidgets('loading nao mostra o card; transiciona pra data', (tester) async {
    final completer = Completer<RedeAparelhosDto>();
    await tester.pumpWidget(wrap([
      redeAparelhosProvider.overrideWith((ref) => completer.future),
    ]));
    await tester.pump(); // frame de loading
    expect(find.text('Minha Rede'), findsNothing);
    completer.complete(dto(encontrada: true, total: 3, saude: 'boa'));
    await tester.pumpAndSettle();
    expect(find.text('Minha Rede'), findsOneWidget);
  });
}
