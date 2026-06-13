# iOS 26 Fase 5 (Cliente detalhe) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** iOS 26 no detalhe do cliente — header de vidro com voltar (fallback /clientes) + corpo em slivers.

**Architecture:** `IosGlassHeader` ganha `Widget? leading`. `cliente_detail_screen.dart` troca `AppBar`+`ListView` por `CustomScrollView` com header de vidro + conteúdo em slivers; fundo `scheme.surface`.

**Tech Stack:** Flutter (Material 3), `SliverAppBar`, `SliverFillRemaining`/`SliverToBoxAdapter`.

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`.

---

## File Structure
- **Modify:** `lib/core/ui/ios_glass_header.dart` — add `leading`.
- **Modify:** `lib/features/clientes/cliente_detail_screen.dart` — header de vidro + slivers.

---

### Task 1: `IosGlassHeader.leading`

**Files:** Modify `lib/core/ui/ios_glass_header.dart`

- [ ] **Step 1: Adicionar o campo `leading`**

Atualizar o construtor e os campos:
```dart
  const IosGlassHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actions = const [],
    this.showBackButton = false,
    this.leading,
  });

  final String title;
  final String? subtitle;
  final List<Widget> actions;
  final bool showBackButton;
  final Widget? leading;
```

- [ ] **Step 2: Passar `leading` pro `SliverAppBar`**

No `SliverAppBar`, logo após `automaticallyImplyLeading: showBackButton,`, adicionar:
```dart
      leading: leading,
```
(Quando `leading != null` o `SliverAppBar` o usa; quando null, cai no `automaticallyImplyLeading`.)

- [ ] **Step 3: Commit**

```bash
git add lib/core/ui/ios_glass_header.dart
git commit --no-verify -m "feat(tecnico-mobile): IosGlassHeader aceita leading customizado"
```

---

### Task 2: Cliente detalhe com header de vidro + slivers

**Files:** Modify `lib/features/clientes/cliente_detail_screen.dart`

- [ ] **Step 1: Import**

Adicionar:
```dart
import '../../core/ui/ios_glass_header.dart';
```

- [ ] **Step 2: Reescrever o `build` de `ClienteDetailScreen`**

Substituir o `return Scaffold(...)` por:
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      body: CustomScrollView(
        slivers: [
          IosGlassHeader(
            title: 'Cliente',
            leading: BackButton(
              onPressed: () =>
                  context.canPop() ? context.pop() : context.go('/clientes'),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Atualizar',
                onPressed: () {
                  ref.invalidate(clienteDetailProvider(id));
                  ref.invalidate(clienteOsHistoricoProvider(id));
                },
              ),
            ],
          ),
          async.when(
            loading: () => const SliverFillRemaining(
              hasScrollBody: false,
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => SliverFillRemaining(
              hasScrollBody: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
                child: AppStatePanel.error(
                  title: 'Não foi possível carregar este cliente',
                  message:
                      'Os dados de detalhe não responderam como esperado. Atualize novamente em instantes.',
                  detail: e is DioException
                      ? extractDioMessage(e, fallback: '')
                      : null,
                  actionLabel: 'Tentar novamente',
                  onAction: () => ref.invalidate(clienteDetailProvider(id)),
                ),
              ),
            ),
            data: (c) => SliverToBoxAdapter(child: _Body(cliente: c)),
          ),
        ],
      ),
    );
```

- [ ] **Step 3: Converter `_Body.build` de ListView pra Column**

Em `_Body.build`, trocar:
```dart
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
```
por:
```dart
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
```
E o fechamento do `ListView` (no fim do build de `_Body`):
```dart
      ],
    );
```
vira:
```dart
        ],
      ),
    );
```
Os filhos (Header card, `_SecaoEndereco`, gaps, `_SecaoConexao`, `_SecaoInstalacao`, `ClienteMateriaisSection`, `_SecaoSimples` observação condicional, `ClienteFotosSection`, card do Histórico de OS) ficam EXATAMENTE iguais — só o wrapper muda. Não alterar nenhum filho.

- [ ] **Step 4: Analyze (deploy)**

Run: `flutter analyze lib/features/clientes/cliente_detail_screen.dart lib/core/ui/ios_glass_header.dart`
Expected: `No issues found!` (rodar `dart format` no arquivo se acusar formatação dos filhos re-indentados).

- [ ] **Step 5: Commit**

```bash
git add lib/features/clientes/cliente_detail_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Cliente detalhe com header de vidro + voltar (iOS 26)"
```

---

### Task 3: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/clientes/ lib/core/ui/ios_glass_header.dart` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - barra de vidro "Cliente" com **voltar** (esquerda) + atualizar; conteúdo rola sob o vidro;
  - voltar funciona (e, chegando via deep link sem pilha, cai em /clientes);
  - fundo cinza, todas as seções (Header/Endereço/Conexão/Instalação/Materiais/Fotos/Histórico) iguais;
  - OS lista/detalhe, Estoque, Clientes lista intactos (header sem `leading` igual).

---

## Self-Review

**Spec coverage:**
- `IosGlassHeader.leading` opcional → Task 1. ✅
- Cliente detalhe: header de vidro + voltar-com-fallback + refresh (invalida 2 providers) → Task 2 Step 2. ✅
- Fundo `surfaceContainerLowest`→`surface` → Task 2 Step 2. ✅
- `_Body` ListView→Column(stretch), filhos iguais → Task 2 Step 3. ✅
- loading/erro em `SliverFillRemaining` (erro preserva AppStatePanel.error + detail Dio) → Task 2 Step 2. ✅
- Telas existentes intactas (leading default null) → Task 1 não quebra. ✅

**Placeholder scan:** sem TBD; código completo.

**Type consistency:** `IosGlassHeader(leading: Widget?)` opcional; `BackButton(onPressed:)`; `context.canPop()/pop()/go` (go_router já importado); `extractDioMessage`/`AppStatePanel.error`/`clienteOsHistoricoProvider` já usados no arquivo.
