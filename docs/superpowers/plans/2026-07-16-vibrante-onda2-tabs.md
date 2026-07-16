# Identidade Vibrante — Onda 2: tabs Faturas, Suporte e Perfil

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar a identidade "Vibrante de marca" (capa ciano + folha) nas 3 tabs restantes do MainShell — Faturas, Suporte e Perfil — sem mudar nenhuma lógica.

**Architecture:** Cada tela adota o padrão consolidado na Onda 1 (spec `docs/superpowers/specs/2026-07-15-redesign-login-home-cliente-design.md`): `Scaffold` → `Column` [capa compacta de altura natural (`CapaBackground`) + `Expanded(FolhaContainer(overlap: radiusFolha, child: <conteúdo scrollável>))`]. O conteúdo existente de cada tela migra pra folha sem alteração de lógica; só a casca (header/título) muda.

**Tech Stack:** Flutter, widgets já existentes: `CapaBackground`/`FolhaContainer` (lib/core/ui/capa_folha.dart), tokens `BrandTokens.capaInk`/`gradientCapa`/`radiusFolha`/`displayGreeting`.

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO dar push.
- ZERO mudança de lógica/estado/providers/navegação — só casca visual. Handlers, controllers, RefreshIndicators, tabs, pull-to-refresh e auto-hides preservados.
- Padrão de capa das tabs (sem botão voltar — são tabs): título display no estilo do reset (`TextStyle(color: capaInk, fontSize: 24, fontWeight: w900, letterSpacing: -0.6)`), padding top `MediaQuery.paddingOf(context).top + BrandTokens.spaceMd`, bottom `BrandTokens.spaceLg + BrandTokens.radiusFolha`, horizontal `BrandTokens.spaceLg`.
- Estrutura: capa de altura natural + `Expanded(FolhaContainer(overlap: BrandTokens.radiusFolha, child: ...))`; listas scrollam DENTRO da folha. Padding bottom das listas ≥ 120 (navbar flutuante).
- Modo escuro: capa igual; folha/cards via FolhaContainer e cores já theme-aware das telas.
- Gate por task: `flutter test` verde (15) + `flutter analyze lib test` ZERO errors/warnings, sem issues novas (159 infos pré-existentes). NUNCA `git add -A` (WIP alheio em lib/features/conexao/conexao_screen.dart).
- Cada task: ler a tela INTEIRA antes de editar (são arquivos grandes); mexer só na casca.

---

### Task 1: Faturas com capa + folha

**Files:**
- Modify: `lib/features/faturas/faturas_screen.dart`

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer`, tokens. Referência de padrão: `lib/features/auth/forgot_reset_screen.dart` (capa compacta) e `lib/features/home/home_screen.dart` (folha com lista).

- [ ] **Step 1: Ler a tela inteira** (794 linhas). Identificar: o `Scaffold`/`SafeArea`/`ListView` externo e o título inline (Text perto da linha 52). TODO o resto (cards de fatura, QR Pix, estados, providers) fica intacto.
- [ ] **Step 2: Reestruturar a casca.** `Scaffold` → `Column`: capa (`CapaBackground` com título `Faturas` no padrão global + subtítulo opcional se a tela já tiver um texto de apoio hoje — mover pra capa em `capaInk` 70%) + `Expanded(FolhaContainer(overlap: radiusFolha, child: <ListView existente>))`. O título inline antigo sai da lista. `SafeArea` do topo sai (capa cuida do inset); manter comportamento de scroll/refresh existente. Padding da lista: remover o horizontal se a FolhaContainer já der (usar `FolhaContainer(padding: EdgeInsets.zero)` e manter o padding atual da lista, ajustando top pra `BrandTokens.spaceMd` e bottom ≥ 120 — o que exigir menos mexida).
- [ ] **Step 3: Gates.** `flutter test` (15 verdes) e `flutter analyze lib test` (0 err/warn, sem novas).
- [ ] **Step 4: Commit.** `git add lib/features/faturas/faturas_screen.dart` + `git commit -m "feat(cliente): faturas com capa vibrante + folha"`.

---

### Task 2: Suporte com capa + folha (TabBar na capa)

**Files:**
- Modify: `lib/features/suporte/suporte_screen.dart`

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer`, tokens. A tela hoje usa `GlassAppBar(title: 'Suporte', actions: [FAQ], bottom: TabBar)` com `extendBodyBehindAppBar` e compensação de altura manual.

- [ ] **Step 1: Ler a tela inteira** (163 linhas) + entender o `TabBarView` (ChatTab + lista de chamados) e a compensação `headerH`.
- [ ] **Step 2: Reestruturar.** Remover `GlassAppBar`/`extendBodyBehindAppBar`/compensação. `Column`: capa com linha [título `Suporte` + IconButton FAQ (`Icons.help_outline_rounded`, cor `capaInk`)] e, abaixo (ainda na capa), o `TabBar` existente restilizado pro fundo ciano: `labelColor: Colors.white`, `unselectedLabelColor: BrandTokens.capaInk.withValues(alpha: 0.55)`, `indicatorColor: Colors.white`, `dividerColor: Colors.transparent`. Depois `Expanded(FolhaContainer(overlap: radiusFolha, padding: EdgeInsets.zero, child: TabBarView existente))`. Controller/tabs/rotas intactos. Atenção: o padding bottom da capa fica APÓS o TabBar (TabBar é o último filho da capa; manter respiro `spaceSm` entre título e TabBar).
- [ ] **Step 3: Gates.** Idem Task 1.
- [ ] **Step 4: Commit.** `git add lib/features/suporte/suporte_screen.dart` + `git commit -m "feat(cliente): suporte com capa vibrante + TabBar na capa"`.

---

### Task 3: Perfil com capa + folha (avatar absorvido)

**Files:**
- Modify: `lib/features/perfil/perfil_screen.dart`

**Interfaces:**
- Consumes: `CapaBackground`, `FolhaContainer`, tokens. A tela tem `_ProfileHeader` (avatar gradient + nome + plano) como primeiro item da lista.

- [ ] **Step 1: Ler a tela inteira** (610 linhas). Mapear `_ProfileHeader` e os estados loading/error do `meProvider`.
- [ ] **Step 2: Reestruturar.** `Column`: capa contendo o conteúdo do `_ProfileHeader` adaptado (avatar circular com iniciais como está, nome em `displayGreeting`, plano em `capaInk` 70%; remover estilos que dependiam do fundo claro) + `Expanded(FolhaContainer(overlap: radiusFolha, child: ListView com o resto dos itens))`. `_ProfileHeader` deixa de ser usado — se ficar sem referência, deletar a classe. Estados loading/error do `meProvider`: capa mostra skeleton/fallback simples no mesmo padrão da home (`_CapaSkeleton` local: Container gradientCapa altura ~180 com CircularProgressIndicator branco; erro: capa com título `Perfil` sem dados e lista segue). Toda a lista de opções/ações/logout intacta.
- [ ] **Step 3: Gates.** Idem Task 1.
- [ ] **Step 4: Commit.** `git add lib/features/perfil/perfil_screen.dart` + `git commit -m "feat(cliente): perfil com capa vibrante + folha"`.

---

### Task 4: Verificação da onda

- [ ] **Step 1:** `flutter test` (15 verdes) + `flutter analyze lib test` (0 err/warn) + `flutter build apk --debug` ok.
- [ ] **Step 2:** Review whole-branch da onda (base = commit anterior à Task 1).
- [ ] **Step 3:** Checklist manual (Robert, pós-push): navegar pelas 4 tabs — capas consistentes, dark mode, TabBar do suporte legível, refresh de faturas, logout no perfil.
