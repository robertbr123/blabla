# GlassAppBar nas telas restantes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar o `GlassAppBar` nas 8 telas que ainda usam `AppBar` sólido, fechando a inconsistência visual "duas camadas" (telas com transição nova mas appbar antigo).

**Architecture:** Mesma receita já validada no design boost (Task 3): trocar `AppBar(...)` por `GlassAppBar(...)`, ligar `extendBodyBehindAppBar: true` no Scaffold, e compensar o topo do conteúdo (padding nos scrollables; SizedBox no topo de Columns não-scrolláveis). `GlassAppBar` (lib/core/ui/glass_app_bar.dart) é drop-in: `GlassAppBar({required String title, List<Widget>? actions, Widget? leading, PreferredSizeWidget? bottom})`.

**Tech Stack:** Flutter 3.44 / Riverpod / GoRouter. Package: `cliente_mobile`.

**Regras:** commits locais com paths explícitos (NUNCA `git add .` — sessão paralela no tecnico-mobile); **NUNCA git push** sem OK. Convenção `withValues(alpha:)`. CI: `flutter analyze` (warning/error quebram; info não) + `flutter test`. Leia cada tela INTEIRA antes de editar.

**Fora de escopo (NÃO mexer):** `promocao_detalhe_screen.dart` (SliverAppBar com FlexibleSpace/Hero — incompatível com drop-in), fluxo de auth (`AuthScaffold`), tabs do shell sem appbar (home/faturas/perfil), splash, login.

## Receita padrão (vale pra todas as telas deste plano)

1. Adicionar import: `import '../../core/ui/glass_app_bar.dart';` (ajustar `../` ao nível da pasta — telas em `features/<x>/` usam `../../core/...`).
2. Trocar `appBar: AppBar(title: Text('X'), ...)` por `appBar: GlassAppBar(title: 'X', ...)` preservando `actions`/`leading`/`bottom` existentes. Descartar `elevation: 0` (o GlassAppBar já é flat). `title` é String (não `Text`).
3. Adicionar `extendBodyBehindAppBar: true` no mesmo `Scaffold`.
4. Compensar o topo do conteúdo com a constante `topPad = MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd`:
   - **Body scrollável** (`ListView`/`SingleChildScrollView`): adicionar/ajustar o `padding` superior pra `topPad`. Se tem `SafeArea` em volta, trocar por `SafeArea(top: false, ...)`.
   - **Body Column não-scrollável**: inserir `SizedBox(height: MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd)` como PRIMEIRO filho (igual fizemos na FAQ). Manter `SafeArea(top: false)` se havia SafeArea.
   - **RefreshIndicator**: setar `edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight` (sem o spaceMd) pra o indicador nascer abaixo do appbar.
5. `flutter analyze` no arquivo após cada tela.

---

### Task 1: Telas scrolláveis simples (contatos, legal, faq_artigo, notif_prefs)

**Files:**
- Modify: `lib/features/contatos/contatos_screen.dart`
- Modify: `lib/features/legal/legal_screen.dart`
- Modify: `lib/features/faq/faq_artigo_screen.dart`
- Modify: `lib/features/notificacoes/notif_prefs_screen.dart`

- [ ] **Step 1: contatos_screen.dart**

Hoje: `AppBar(title: const Text('Fale conosco'))`; body `RefreshIndicator > async.when > ListView.separated`.
- `GlassAppBar(title: 'Fale conosco')` + `extendBodyBehindAppBar: true`.
- No `ListView.separated`: garantir `padding` com topo = `topPad` (se já tem padding, ajustar o top; senão adicionar `padding: EdgeInsets.fromLTRB(spaceMd, topPad, spaceMd, spaceLg)` conforme o estilo atual).
- `RefreshIndicator`: `edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight`.
- Estados loading/error do `async.when`: se forem `Center(...)` não precisam de compensação (centralizados). Se forem scrolláveis, aplicar topPad.

- [ ] **Step 2: legal_screen.dart**

Hoje: `AppBar(title: Text(title))`; body `SafeArea > SingleChildScrollView > Text`.
- `GlassAppBar(title: title)` + `extendBodyBehindAppBar: true`.
- `SafeArea` → `SafeArea(top: false, ...)`.
- `SingleChildScrollView`: `padding` com topo = `topPad` (preservar o padding horizontal/inferior que já existe).

- [ ] **Step 3: faq_artigo_screen.dart**

Tem DOIS Scaffolds:
- Caso erro (`AppBar(title: const Text('Artigo'))` + `body: Center(...)`): trocar por `GlassAppBar(title: 'Artigo')` + `extendBodyBehindAppBar: true`. O `Center` fica (não precisa compensar).
- Caso principal (`AppBar(title: const Text(''), elevation: 0)` + `body: ListView`): trocar por `GlassAppBar(title: '')` + `extendBodyBehindAppBar: true`; no `ListView`, padding topo = `topPad` (preservar o resto).

- [ ] **Step 4: notif_prefs_screen.dart**

Hoje: `AppBar(title: 'Preferências', elevation: 0)`; body `async.when > ListView`.
- `GlassAppBar(title: 'Preferências')` + `extendBodyBehindAppBar: true`.
- `ListView`: padding topo = `topPad`. Estados loading/error: se `Center`, não compensar.

- [ ] **Step 5: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: sem warning/error novos; testes PASS.

```bash
git add lib/features/contatos/contatos_screen.dart lib/features/legal/legal_screen.dart lib/features/faq/faq_artigo_screen.dart lib/features/notificacoes/notif_prefs_screen.dart
git commit -m "polish(app): GlassAppBar em contatos, legal, faq-artigo e notif-prefs"
```

---

### Task 2: Forms com Column não-scrollável (editar_perfil, mudar_senha)

**Files:**
- Modify: `lib/features/perfil/editar_perfil_screen.dart`
- Modify: `lib/features/perfil/mudar_senha_screen.dart`

Ambas: body `SafeArea > Padding > Column` com TextField(s) + `Spacer()` + botão no rodapé. Como a Column não rola, o conteúdo do topo ficaria atrás do appbar com `extendBodyBehindAppBar`.

- [ ] **Step 1: editar_perfil_screen.dart**

Hoje: `AppBar(title: Text(label))`.
- `GlassAppBar(title: label)` + `extendBodyBehindAppBar: true`.
- `SafeArea` → `SafeArea(top: false, ...)`.
- Inserir como PRIMEIRO filho da `Column`: `SizedBox(height: MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd)`.
- Conferir que `BrandTokens` está importado (provavelmente sim).

- [ ] **Step 2: mudar_senha_screen.dart**

Hoje: `AppBar(title: const Text('Mudar senha'))`. Mesma estrutura.
- `GlassAppBar(title: 'Mudar senha')` + `extendBodyBehindAppBar: true`.
- `SafeArea` → `SafeArea(top: false, ...)`.
- Inserir `SizedBox(height: MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd)` como primeiro filho da `Column`.

- [ ] **Step 3: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/features/perfil/editar_perfil_screen.dart lib/features/perfil/mudar_senha_screen.dart
git commit -m "polish(app): GlassAppBar em editar-perfil e mudar-senha"
```

---

### Task 3: Novo Chamado (wizard com leading + actions + triagem)

**Files:**
- Modify: `lib/features/suporte/novo_chamado_screen.dart`

Hoje: `AppBar(title: ..., leading: IconButton(close), actions: [FAQ IconButton])`; body `SafeArea > Padding > Column` (wizard de steps; um dos caminhos é a `TriagemRede` da v3, outros são `ListView`).

- [ ] **Step 1: Converter**

- `GlassAppBar(title: 'Novo chamado', leading: <o IconButton de fechar atual>, actions: <as actions atuais>)` — preservar leading e actions EXATAMENTE como estão.
- `extendBodyBehindAppBar: true`.
- `SafeArea` → `SafeArea(top: false, ...)`.
- Compensar o topo do conteúdo do wizard: o body é uma `Column`/`Padding`. Inserir um `SizedBox(height: MediaQuery.paddingOf(context).top + kToolbarHeight + BrandTokens.spaceMd)` no topo do conteúdo visível de cada step (ou um único no topo da Column raiz, se a estrutura permitir sem quebrar o layout dos steps). **Cuidado:** a `TriagemRede` é renderizada como conteúdo do step de `sem_internet` — ela já tem o próprio layout; garantir que ela também não fique atrás do appbar (a triagem ocupa a tela toda do step). Se a triagem tiver scroll/centralização próprios, avaliar; se ficar complexo, aplicar o SizedBox de topo no container que envolve o conteúdo do step antes de renderizar a triagem.
- Leia a tela inteira e ajuste com cuidado pra não desalinhar o wizard. Se algo não couber na receita, reporte como DONE_WITH_CONCERNS descrevendo o que fez.

- [ ] **Step 2: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/features/suporte/novo_chamado_screen.dart
git commit -m "polish(app): GlassAppBar no novo chamado (preserva fechar + FAQ + triagem)"
```

---

### Task 4: Suporte (shell tab com TabBar + Stack + FAB)

**Files:**
- Modify: `lib/features/suporte/suporte_screen.dart`

⚠️ Tela mais delicada: é tab do shell (índice 2 do MainShell), tem `AppBar(title: 'Suporte', actions: [...], bottom: TabBar(length 2))`, body `Stack > [TabBarView (chat + chamados), FAB posicionado]`. O FAB é posicionado manualmente referenciando `extendBody:true` do shell.

- [ ] **Step 1: Converter o AppBar mantendo a TabBar**

- `GlassAppBar(title: 'Suporte', actions: <as actions atuais>, bottom: <a TabBar atual>)` — a `TabBar` é `PreferredSizeWidget`, então cabe no `bottom`. Preservar o `TabController` e a TabBar inalterados.
- `extendBodyBehindAppBar: true` no Scaffold da tela.
- **Compensação dupla:** com o appbar de vidro + TabBar no bottom, a altura total do header = `kToolbarHeight + alturaDaTabBar (~48)`. O conteúdo das duas abas (chat e chamados) precisa começar abaixo disso. Definir `final headerH = MediaQuery.paddingOf(context).top + kToolbarHeight + 48;` e aplicar como padding/topo no conteúdo de cada aba:
  - Aba "chamados" (`ListView`/`ListView.builder`): `padding` topo = `headerH + BrandTokens.spaceSm`; `RefreshIndicator` (se houver) com `edgeOffset: MediaQuery.paddingOf(context).top + kToolbarHeight + 48`.
  - Aba "chat" (`ChatTab`): o conteúdo do chat (lista de mensagens) precisa começar abaixo do header — aplicar padding topo equivalente no scroll do chat. Se o ChatTab for um widget separado, pode ser necessário passar o offset ou ajustar dentro dele; leia o ChatTab e decida o ponto mínimo de mudança.
- O FAB posicionado: conferir que continua acima da navbar do shell (a posição inferior não muda; só o topo é afetado).

- [ ] **Step 2: Se a compensação do chat ficar invasiva, reportar**

Se ajustar o ChatTab exigir mudança grande (mais que padding), pare e reporte DONE_WITH_CONCERNS com o que encontrou — podemos decidir manter o chat como está e converter só o resto, ou tratar o ChatTab à parte. Não force uma refatoração grande do chat aqui.

- [ ] **Step 3: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/features/suporte/suporte_screen.dart
git commit -m "polish(app): GlassAppBar na aba Suporte (TabBar de vidro)"
```

(Se tocar no ChatTab, incluir o arquivo no `git add` e citar no commit.)

---

### Task 5: Verificação final

- [ ] **Step 1:** `flutter analyze` — 0 warning/error no código do projeto (ignorar ruído de `build/ios/SourcePackages`).
- [ ] **Step 2:** `flutter test` — todos PASS (contagem deve bater com antes; este plano não adiciona testes, só muda telas).
- [ ] **Step 3:** Smoke conceitual: as 8 telas abrem com appbar de vidro, conteúdo rola por baixo sem nada escondido no topo, leading/actions/TabBar preservados, claro e escuro ok. Confirmar que `promocao_detalhe` (SliverAppBar) e auth seguem intocados.
- [ ] **Step 4:** Aguardar OK do Robert pra push.
