# iOS 26 Fase 7 (Perfil + Rede + Login) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Fechar o iOS 26 nas 3 telas restantes reusando `IosGlassHeader` (Perfil/Rede) e fundo agrupado (Login). Sem componente novo.

**Tech Stack:** Flutter (Material 3), `SliverFillRemaining`/`SliverToBoxAdapter`/`SliverPadding`.

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`. Sem teste automatizado (refactor visual).

---

## File Structure
- **Modify:** `lib/features/auth/login_screen.dart` (bg).
- **Modify:** `lib/features/perfil/perfil_screen.dart` (header sliver).
- **Modify:** `lib/features/rede/rede_screen.dart` (header sliver + voltar).

---

### Task 1: Login — fundo agrupado

**Files:** Modify `lib/features/auth/login_screen.dart`

- [ ] **Step 1: Trocar o backgroundColor**

Trocar (no `build`):
```dart
      backgroundColor: scheme.surfaceContainerLowest,
```
por:
```dart
      backgroundColor: scheme.surface,
```
(Só isso. Nenhuma outra mudança — sem AppBar, form igual.)

- [ ] **Step 2: Commit**

```bash
git add lib/features/auth/login_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Login com fundo agrupado iOS 26"
```

---

### Task 2: Perfil — header de vidro + slivers

**Files:** Modify `lib/features/perfil/perfil_screen.dart`

- [ ] **Step 1: Import**

Adicionar junto aos imports de `core/ui`:
```dart
import '../../core/ui/ios_glass_header.dart';
```

- [ ] **Step 2: Reescrever o `return Scaffold(...)` de `PerfilScreen.build`**

Substituir o `Scaffold` inteiro por (mantendo os MESMOS filhos do ListView dentro do Column):
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(perfilProvider),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            IosGlassHeader(
              title: 'Perfil',
              actions: [
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Atualizar',
                  onPressed: () => ref.invalidate(perfilProvider),
                ),
              ],
            ),
            ...async.when<List<Widget>>(
              loading: () => const [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _StateBody(
                    child: AppStatePanel.loading(
                      title: 'Carregando seu perfil',
                      message: 'Preparando foto, status e estatísticas.',
                    ),
                  ),
                ),
              ],
              error: (e, _) => [
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _ErroView(
                    e: e,
                    onRetry: () => ref.invalidate(perfilProvider),
                  ),
                ),
              ],
              data: (p) => [
                SliverPadding(
                  padding: EdgeInsets.fromLTRB(
                    16,
                    12,
                    16,
                    32 + 74 + MediaQuery.paddingOf(context).bottom,
                  ),
                  sliver: SliverToBoxAdapter(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _Header(perfil: p),
                        const SizedBox(height: 20),
                        const _SectionTitle('Atividade do mês'),
                        const SizedBox(height: 8),
                        _StatsGrid(stats: p.estatisticas),
                        const SizedBox(height: 20),
                        const _SectionTitle('Conta'),
                        const SizedBox(height: 8),
                        _ActionTile(
                          icon: Icons.lock_outline,
                          title: 'Mudar senha',
                          onTap: () => _openMudarSenha(context),
                        ),
                        const SizedBox(height: 8),
                        _ActionTile(
                          icon: Icons.logout,
                          title: 'Sair',
                          destructive: true,
                          onTap: () => _logout(context, ref),
                        ),
                        const SizedBox(height: 20),
                        const _SectionTitle('Sobre'),
                        const SizedBox(height: 8),
                        _InfoTile(
                          icon: Icons.smartphone,
                          label: 'Versão',
                          value: '0.1.0',
                          onTap: () => _maybeRevealEasterEgg(context),
                        ),
                        const SizedBox(height: 8),
                        const _InfoTile(
                            icon: Icons.business,
                            label: 'Empresa',
                            value: 'Linket'),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
```
(`_openMudarSenha`/`_logout` e os widgets `_Header`/`_StatsGrid`/`_ActionTile`/`_InfoTile`/`_SectionTitle` ficam IGUAIS.)

- [ ] **Step 3: Analyze (deploy)** — `flutter analyze lib/features/perfil/perfil_screen.dart`. (Se `_StatsGrid` reclamar de altura no Column, é porque é GridView sem shrinkWrap — improvável, já estava num ListView; nesse caso adicionar `shrinkWrap: true` + `physics: NeverScrollableScrollPhysics()` no GridView do `_StatsGrid`.)

- [ ] **Step 4: Commit**

```bash
git add lib/features/perfil/perfil_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Perfil com header de vidro (iOS 26)"
```

---

### Task 3: Rede — header de vidro + voltar + slivers

**Files:** Modify `lib/features/rede/rede_screen.dart`

- [ ] **Step 1: Import**

```dart
import '../../core/ui/ios_glass_header.dart';
```

- [ ] **Step 2: Reescrever o `return Scaffold(...)` de `build`**

Substituir por:
```dart
    return Scaffold(
      backgroundColor: scheme.surface,
      body: CustomScrollView(
        slivers: [
          IosGlassHeader(
            title: 'Rede do cliente',
            showBackButton: true,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Atualizar',
                onPressed: () {
                  ref.invalidate(redeStatusProvider(widget.cpf));
                  ref.invalidate(redeDiagnosticoProvider(widget.cpf));
                },
              ),
            ],
          ),
          ...status.when<List<Widget>>(
            loading: () => const [
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(child: CircularProgressIndicator()),
              ),
            ],
            error: (e, _) => [
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('Erro ao carregar a rede.'),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: () =>
                            ref.invalidate(redeStatusProvider(widget.cpf)),
                        child: const Text('Tentar novamente'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            data: (s) => [SliverToBoxAdapter(child: _body(s))],
          ),
        ],
      ),
    );
```
(Precisa de `final scheme = Theme.of(context).colorScheme;` no início do `build` — adicionar se não existir.)

- [ ] **Step 3: Converter `_body(StatusRede s)` de ListView pra Column**

No método `_body`, trocar:
```dart
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
```
por:
```dart
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
```
E o fechamento do ListView:
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
Os filhos (status row, redes ListTiles, dividers, `_diagnostico()`, campo serial, campo senha, botão "Trocar senha do WiFi", nota offline) ficam IGUAIS.

- [ ] **Step 4: Analyze (deploy)** — `flutter analyze lib/features/rede/rede_screen.dart`.

- [ ] **Step 5: Commit**

```bash
git add lib/features/rede/rede_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): Rede com header de vidro + voltar (iOS 26)"
```

---

### Task 4: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/perfil/ lib/features/rede/ lib/features/auth/login_screen.dart` → limpo.
- [ ] **Step 2: Visual on-device (claro/escuro):**
  - Perfil: header de vidro "Perfil" + atualizar; stats/ações rolando; última opção não fica atrás do navbar; mudar senha/logout/easter-egg ok.
  - Rede: header de vidro "Rede do cliente" com voltar + atualizar; sinal/aparelhos/trocar senha WiFi ok; voltar funciona.
  - Login: fundo cinza; form/biometria/entrar ok.

---

## Self-Review

**Spec coverage:**
- Login bg `surfaceContainerLowest`→`surface` → Task 1. ✅
- Perfil header de vidro + slivers + folga navbar preservada (SliverPadding) → Task 2. ✅
- Rede header de vidro + voltar + slivers, `_body` ListView→Column → Task 3. ✅
- loading/erro em `SliverFillRemaining` (perfil e rede) → Tasks 2-3. ✅
- Lógica/dados intactos nas 3. ✅

**Placeholder scan:** sem TBD; código completo (filhos do Perfil reproduzidos; filhos do Rede mantidos via conversão de wrapper).

**Type consistency:** `async.when<List<Widget>>`/`status.when<List<Widget>>` nos branches; `IosGlassHeader(showBackButton:true)` no Rede; `_body(StatusRede)` segue método da State; `_StateBody`/`_ErroView` (perfil) e `_diagnostico` (rede) inalterados.
