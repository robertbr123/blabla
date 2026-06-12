# iOS 26 — Fase 1: OS lista + componentes compartilhados — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/os/os_list_screen.dart` (depende da Fundação Fase 0, já entregue)

## Objetivo

Aplicar o look iOS 26 na tela de OS lista e, no caminho, criar os **2 componentes
reutilizáveis** que as próximas fases por-tela vão consumir:
1. `IosGlassHeader` — header large-title de vidro (a assinatura visual do iOS 26).
2. `AppSegmentedControl<T>` — seletor segmentado estilo iOS.

Decisões aprovadas pelo Robert:
- Manter os **KPI cards** (já herdam o card arredondado da Fase 0).
- Trocar o **strip de chips** (`HomeFilterStrip`) pelo `AppSegmentedControl`.
- Título do header: **"Ordens de Serviço"**.

Política mantida: vidro só no chrome (header), conteúdo sólido.

## Componentes novos (em `lib/core/ui/`)

### `IosGlassHeader` (`ios_glass_header.dart`)
Header large-title de vidro, pensado pra entrar como **primeiro sliver** de um
`CustomScrollView` (a OS lista já usa um).

- Baseado em `SliverAppBar.large` (`pinned: true`): mostra o título grande embaixo
  e colapsa pro título inline ao rolar — comportamento large-title nativo do iOS.
- Fundo **translúcido com blur**: `backgroundColor` semi-transparente
  (`scheme.surface.withValues(alpha: 0.7)`) + `flexibleSpace` com
  `ClipRect` → `BackdropFilter(ImageFilter.blur(sigma ~18))` pra desfocar o
  conteúdo que rola por baixo. `surfaceTintColor: Colors.transparent`,
  `elevation: 0`, `scrolledUnderElevation: 0` (a separação vem do blur, não de sombra).
- API:
  ```dart
  IosGlassHeader({
    required String title,
    String? subtitle,
    List<Widget> actions = const [],
  })
  ```
  `subtitle` (opcional) aparece como linha secundária menor sob o large title quando
  expandido. `actions` são os `IconButton` da direita (refresh, sair etc).
- Retorna um `Widget` que É um sliver (extends nada — é um `StatelessWidget` cujo
  `build` devolve o `SliverAppBar`). Reutilizável por qualquer tela com
  `CustomScrollView`.

### `AppSegmentedControl<T>` (`app_segmented_control.dart`)
Seletor segmentado estilo iOS — track arredondado com pílula deslizante.

- API:
  ```dart
  AppSegmentedControl<T>({
    required List<AppSegment<T>> segments, // value + label
    required T selected,
    required ValueChanged<T> onChanged,
  })
  // class AppSegment<T> { final T value; final String label; }
  ```
- Visual: um track `surfaceContainerHigh` (raio ~12); o segmento selecionado é uma
  **pílula branca** (`surface`/branco) com sombra suave + texto `scheme.primary`
  (emerald) peso 700; não-selecionados texto `onSurfaceVariant`. Pílula desliza com
  `AnimatedAlign`/`AnimatedPositioned` (~220ms easeOut).
- **Largura:** segmentos dimensionados pelo conteúdo; o track inteiro fica num
  `SingleChildScrollView` horizontal — quando os 5 filtros não cabem, rola sem
  truncar (labels longos como "Em andamento" ficam inteiros).
- Haptic `selectionClick` na troca. `Semantics(button, selected, label)` por segmento.

## Mudanças na OS lista (`os_list_screen.dart`)

- O `Scaffold.appBar` (AppBar atual sem título, só ícones) é **removido**; o
  `IosGlassHeader` entra como **primeiro sliver** do `CustomScrollView`:
  - `title: 'Ordens de Serviço'`
  - `subtitle:` dinâmico — `'<n> ordens em foco'` usando o total de itens
    (reaproveita o count já calculado).
  - `actions:` os mesmos dois `IconButton` (refresh → `invalidate(osListStreamProvider)`,
    sair → `_logout`).
- O `loading`/`error` continuam como estão (`_StateBody`/`_Erro`) — só o estado `data`
  ganha o header como primeiro sliver.
- **KPI cards**: inalterados (já herdam Fase 0).
- **Filtros**: o `SliverToBoxAdapter` que hoje renderiza `HomeFilterStrip` passa a
  renderizar `AppSegmentedControl<OsHomeFilter>` com os 5 `OsHomeFilter.values`
  (label via `OsHomeFilterX.label`), `selected: _selectedFilter`,
  `onChanged: _selectFilter`.
- **OsCards / section headers / offline banner / sort / sync / navegação**: inalterados.
- `_logout` e a lógica de filtro/contagem: inalterados.

## Fora de escopo (Fase 1)
- `HomeFilterStrip` fica no repo (não removo agora) caso outra tela use; só deixo de
  ser usada na OS lista. (Se nenhuma outra tela usar, remoção entra numa limpeza futura.)
- Demais telas — fases seguintes.

## Critérios de sucesso
1. OS lista mostra o large title "Ordens de Serviço" de vidro, que colapsa ao rolar
   e desfoca o conteúdo por baixo.
2. Filtros viram segmented control iOS; os 5 estados continuam selecionáveis e
   filtrando igual (comportamento idêntico ao strip).
3. `IosGlassHeader` e `AppSegmentedControl` são genéricos/reutilizáveis (sem
   acoplamento à OS lista) — prontos pras próximas fases.
4. KPI cards, navegação, sort, sync, logout inalterados.
5. `flutter analyze` limpo + testes passando (na máquina de deploy).
6. Visual on-device (claro/escuro): header de vidro convincente, segmented control
   legível, nada quebrado.

## Riscos conhecidos
- `SliverAppBar.large` + `flexibleSpace`/`BackdropFilter`: o blur precisa do `ClipRect`
  pra não vazar; o título grande tem padding próprio — ajustar no plano pra não cortar
  o subtítulo. (Detalhe de implementação, resolvido no plano.)
- `backgroundColor` translúcido no header: em tema claro o conteúdo cinza some bem sob
  o blur; conferir contraste do título sobre o blur no claro e no escuro.
- A tela fixa `backgroundColor: scheme.surface` (já cinza pós-Fase 0) — ok, mantém.
