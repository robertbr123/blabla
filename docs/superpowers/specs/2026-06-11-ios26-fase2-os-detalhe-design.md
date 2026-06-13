# iOS 26 — Fase 2: OS detalhe — Design

**Data:** 2026-06-11 (início do ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/os/os_detail_screen.dart` (depende da Fundação Fase 0 + componentes da Fase 1)

## Objetivo

Aplicar iOS 26 na tela de detalhe da OS, reusando o `IosGlassHeader` (barra compacta
de vidro da Fase 1) — agora estendido com botão de voltar pra telas de detalhe.

## Mudança no componente compartilhado

`IosGlassHeader` ganha um parâmetro `bool showBackButton` (default `false`):
- `false` (telas-raiz, ex: OS lista) → sem leading (como hoje).
- `true` (telas de detalhe via push, ex: OS detalhe) → mostra a setinha de voltar
  nativa (mapeia pra `automaticallyImplyLeading: true` do `SliverAppBar`, que exibe
  o back quando há rota pra popar).

Telas que já usam o header sem o parâmetro continuam idênticas (default false).

## Mudanças na OS detalhe (`os_detail_screen.dart`)

Hoje: `Scaffold(backgroundColor: surfaceContainerLowest, appBar: AppBar('Detalhe da OS' + refresh), body: async.when(...))`, e `_Body` é um `ListView` de seções (todas em `AppSurfaceCard`).

Passa a ser:
1. `Scaffold(backgroundColor: scheme.surface)` (cinza agrupado da Fase 0; era `surfaceContainerLowest` branco) **sem `appBar`**.
2. `body: CustomScrollView` com slivers:
   - 1º sliver: `IosGlassHeader(title: 'Detalhe da OS', showBackButton: true, actions: [IconButton refresh → invalidate(osDetailProvider(id))])`.
   - conteúdo via `async.when`:
     - `loading` → `SliverFillRemaining(hasScrollBody: false, child: Center(CircularProgressIndicator))`.
     - `error` → `SliverFillRemaining(hasScrollBody: false, child: _Erro(...))`.
     - `data` → `SliverToBoxAdapter(child: _Body(osId: id, os: os))`.
3. `_Body.build`: troca o `ListView(padding: fromLTRB(16,12,16,24), children: [...])` por
   `Padding(padding: fromLTRB(16,12,16,24), child: Column(crossAxisAlignment: stretch, children: [...]))`
   — os MESMOS filhos (banner pendente, `_StatusSection`, gaps, `_ContextSection`,
   `_LocationSection` condicional, `_ActionsSection`, `_PhotosSection`). O scroll passa
   a ser do `CustomScrollView` (não mais do ListView interno).

## Não muda
- Seções (`_StatusSection`/`_ContextSection`/`_LocationSection`/`_ActionsSection`/`_PhotosSection`) — só herdam o card da Fase 0.
- Lógica de iniciar/concluir/foto, GPS, `_ConcluirSheet`, dados, providers, navegação.
- Demais telas (fases seguintes).

## Critérios de sucesso
1. OS detalhe mostra a barra compacta de vidro "Detalhe da OS" com **voltar** + atualizar; conteúdo rola sob o vidro.
2. Fundo cinza agrupado, cards brancos destacando.
3. `IosGlassHeader` com `showBackButton` continua funcionando como antes quando não passado (OS lista intacta).
4. Iniciar/concluir/foto e a sheet de conclusão funcionam igual.
5. `flutter analyze` limpo + testes passando (deploy).
6. Visual on-device (claro/escuro): header de vidro com voltar, seções iguais, nada quebrado.

## Riscos
- Trocar `ListView` por `Column` dentro de `SliverToBoxAdapter`: garantir
  `crossAxisAlignment: stretch` pros cards ocuparem a largura (o ListView fazia isso).
- `SliverFillRemaining` no loading/erro: confirmar que centraliza sob o header pinned.
