# Card de destaque "Minha Rede" na home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar destaque ao "Minha Rede" com um card vivo no topo da home (dispositivos conectados + selo de sinal + atalho trocar senha), consumindo o provider existente; some pra quem não tem ONU.

**Architecture:** Spec em `docs/superpowers/specs/2026-06-13-card-destaque-minha-rede-design.md`. Um widget novo `RedeDestaqueCard` (só leitura, observa `redeAparelhosProvider` já existente e contrato-aware) inserido na home entre o HeroCard e o `QuickCardsRow`. Sem backend, sem migration. O ícone "Minha rede" nas "Ações rápidas" PERMANECE (decisão do Robert).

**Tech Stack:** Flutter 3.44 / Riverpod 2 / GoRouter 14. Package name: `cliente_mobile`.

**Regras:** commits locais com paths explícitos (`git add <arquivos>` — NUNCA `git add .`; há sessão paralela no repo no tecnico-mobile). **NUNCA git push** sem OK. Convenção `withValues(alpha:)` (nunca `withOpacity`). CI: `flutter analyze` (warning/error quebram; info não) + `flutter test`.

**Diretório:** `/Users/robertalbino/Developer/blabla/apps/cliente-mobile`

---

### Task 1: Widget RedeDestaqueCard (TDD)

**Files:**
- Create: `lib/features/home/widgets/rede_destaque_card.dart`
- Test: `test/rede_destaque_card_test.dart`

Tipos reais (de `lib/core/api/rede_repository.dart`, já existentes — NÃO recriar):
- `final redeAparelhosProvider = FutureProvider<RedeAparelhosDto>(...)` (observa `contratoAtualProvider` internamente).
- `class RedeAparelhosDto { final bool encontrada; final int total; final List<RedeAparelho> aparelhos; final String saude; }` — construtor `RedeAparelhosDto({required this.encontrada, required this.total, required this.aparelhos, required this.saude})`. `saude` ∈ `excelente | boa | fraca | indisponivel`.

- [ ] **Step 1: Escrever os testes (falhando)**

`test/rede_destaque_card_test.dart`:

```dart
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `flutter test test/rede_destaque_card_test.dart`
Expected: FAIL (arquivo `rede_destaque_card.dart` não existe).

- [ ] **Step 3: Implementar o widget**

`lib/features/home/widgets/rede_destaque_card.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/rede_repository.dart';
import '../../../core/branding/brand_tokens.dart';
import '../../../core/ui/pressable_scale.dart';

/// Card de destaque da Minha Rede na home: dispositivos conectados + selo de
/// sinal ao vivo + atalho de trocar senha. Some pra quem nao tem ONU mapeada
/// (encontrada=false) ou quando a consulta falha — nesses casos o icone em
/// "Acoes rapidas" continua como acesso. Toca -> /rede.
class RedeDestaqueCard extends ConsumerWidget {
  const RedeDestaqueCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(redeAparelhosProvider);
    return async.when(
      loading: () => const _Skeleton(),
      // Erro (rede/GenieACS): nao da pra saber se a ONU existe -> esconde.
      error: (_, __) => const SizedBox.shrink(),
      data: (d) =>
          d.encontrada ? _Card(dados: d) : const SizedBox.shrink(),
    );
  }
}

/// Cores/ícone/label do selo de sinal — espelha o _SaudeBadge da rede_screen,
/// em versão compacta (só o essencial pro chip).
({Color cor, IconData icon, String label}) _selo(String saude) {
  switch (saude) {
    case 'excelente':
      return (
        cor: BrandTokens.success,
        icon: Icons.signal_cellular_alt_rounded,
        label: 'Ótimo',
      );
    case 'boa':
      return (
        cor: BrandTokens.primary,
        icon: Icons.signal_cellular_alt_rounded,
        label: 'Bom',
      );
    case 'fraca':
      return (
        cor: BrandTokens.warning,
        icon: Icons.signal_cellular_alt_2_bar_rounded,
        label: 'Fraco',
      );
    default:
      return (
        cor: BrandTokens.info,
        icon: Icons.wifi_tethering_rounded,
        label: 'Ativo',
      );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.dados});
  final RedeAparelhosDto dados;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? BrandTokens.surfaceDark : BrandTokens.surface;
    final secondary =
        isDark ? BrandTokens.textSecondaryDark : BrandTokens.textSecondary;
    final selo = _selo(dados.saude);
    final n = dados.total;
    final aparelhosLabel =
        '$n ${n == 1 ? 'aparelho conectado' : 'aparelhos conectados'}';

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: PressableScale(
        onTap: () => context.push('/rede'),
        child: Container(
          padding: const EdgeInsets.all(BrandTokens.spaceMd),
          decoration: BoxDecoration(
            color: surface,
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: BrandTokens.shadowCard,
            border: Border.all(
              color: isDark ? Colors.white10 : BrandTokens.divider,
            ),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: BrandTokens.gradientPrimary,
                      borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
                    ),
                    child: const Icon(
                      Icons.wifi_rounded,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: BrandTokens.spaceMd),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Minha Rede',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          aparelhosLabel,
                          style: TextStyle(fontSize: 13, color: secondary),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: selo.cor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(BrandTokens.radiusSm),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(selo.icon, color: selo.cor, size: 14),
                        const SizedBox(width: 4),
                        Text(
                          selo.label,
                          style: TextStyle(
                            color: selo.cor,
                            fontWeight: FontWeight.w700,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Divider(
                height: 1,
                color: isDark ? Colors.white10 : BrandTokens.divider,
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Row(
                children: [
                  Icon(
                    Icons.key_rounded,
                    size: 18,
                    color: isDark ? BrandTokens.primaryLight : BrandTokens.primary,
                  ),
                  const SizedBox(width: BrandTokens.spaceSm),
                  const Expanded(
                    child: Text(
                      'Trocar senha do WiFi',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  Icon(Icons.arrow_forward_rounded, size: 16, color: secondary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Skeleton extends StatelessWidget {
  const _Skeleton();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceLg),
      child: Container(
        height: 104,
        decoration: BoxDecoration(
          color: isDark ? Colors.white10 : BrandTokens.divider,
          borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `flutter test test/rede_destaque_card_test.dart`
Expected: PASS (5 testes).

- [ ] **Step 5: Verificar e commitar**

Run: `flutter analyze lib/features/home/widgets/rede_destaque_card.dart test/rede_destaque_card_test.dart`
Expected: sem warning/error (info ok).

```bash
git add lib/features/home/widgets/rede_destaque_card.dart test/rede_destaque_card_test.dart
git commit -m "feat(app/home): RedeDestaqueCard — card vivo de Minha Rede (dispositivos + sinal + trocar senha)"
```

---

### Task 2: Inserir na home + pull-to-refresh

**Files:**
- Modify: `lib/features/home/home_screen.dart`

- [ ] **Step 1: Importar e inserir o card**

No topo do arquivo, adicionar o import junto dos outros `widgets/`:

```dart
import 'widgets/rede_destaque_card.dart';
```

Localizar o bloco do hero + a linha `const SizedBox(height: BrandTokens.spaceLg)` seguida de `const QuickCardsRow()` (hoje ~linhas 92-96):

```dart
                loading: () => const _HeroSkeleton(),
                error: (_, __) => _CachedHeroOrError(ref),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              const QuickCardsRow(),
```

Inserir o card ENTRE o `SizedBox(spaceLg)` e o `QuickCardsRow` (o card já tem padding inferior `spaceLg` próprio, então separa naturalmente do QuickCardsRow):

```dart
                loading: () => const _HeroSkeleton(),
                error: (_, __) => _CachedHeroOrError(ref),
              ),
              const SizedBox(height: BrandTokens.spaceLg),
              const RedeDestaqueCard(),
              const QuickCardsRow(),
```

- [ ] **Step 2: Incluir no pull-to-refresh**

Localizar o `onRefresh` do `RefreshIndicator` da home (grep `onRefresh` em `home_screen.dart`). Adicionar a invalidação do provider de rede junto das outras invalidações que já existem ali:

```dart
        ref.invalidate(redeAparelhosProvider);
```

(Se o `onRefresh` usar `ref.invalidate(...)` pra outros providers, seguir o mesmo padrão; se usar `meRepository.refresh()` + invalidações, adicionar a linha junto. O `redeAparelhosProvider` já está importado via o import do widget? NÃO — ele vem de `core/api/rede_repository.dart`. Adicionar esse import também se o arquivo ainda não o tiver: `import '../../core/api/rede_repository.dart';`.)

- [ ] **Step 3: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: analyze sem warning/error; todos os testes PASS (incluindo os 5 novos).

```bash
git add lib/features/home/home_screen.dart
git commit -m "feat(app/home): card Minha Rede no topo da home + refresh"
```

---

### Task 3: Verificação final

- [ ] **Step 1:** `flutter analyze` — 0 warning/error no código do projeto (ignorar ruído de `build/ios/SourcePackages`).
- [ ] **Step 2:** `flutter test` — todos PASS; conferir contagem (os 5 novos do card entram).
- [ ] **Step 3:** Smoke conceitual: card aparece abaixo do hero pra cliente com ONU (total + selo + trocar senha), some pra cliente sem ONU, skeleton no load; tocar leva pra `/rede`; ícone "Minha rede" continua em "Ações rápidas"; claro e escuro ok; pull-to-refresh atualiza o card.
- [ ] **Step 4:** Aguardar OK do Robert pra push.
