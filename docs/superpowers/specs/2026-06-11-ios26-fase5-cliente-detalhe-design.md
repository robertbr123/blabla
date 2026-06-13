# iOS 26 — Fase 5: Cliente detalhe — Design

**Data:** 2026-06-11 (ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/clientes/cliente_detail_screen.dart` (push; tem voltar)

## Objetivo
iOS 26 no detalhe do cliente, molde da OS detalhe (header de vidro com voltar + corpo em slivers), preservando o **voltar com fallback** pra `/clientes`.

## Mudança no componente compartilhado
`IosGlassHeader` ganha um **`Widget? leading`** opcional:
- `leading != null` → usado como leading do `SliverAppBar` (telas que precisam de um back customizado).
- `leading == null` → comportamento atual (`automaticallyImplyLeading: showBackButton`).
Sem quebra pros usos existentes (default null).

## Mudanças na Cliente detalhe (`cliente_detail_screen.dart`)
Hoje: `Scaffold(surfaceContainerLowest, appBar: AppBar(leading: BackButton(canPop?pop:go('/clientes')), title 'Cliente', refresh), body: async.when(loading/error/data→_Body))`; `_Body` é `ListView` de seções (Header, Endereço, Conexão, Instalação, Materiais, Observação?, **Fotos**, Histórico OS), todas em `AppSurfaceCard`.

Passa a ser:
1. `Scaffold(backgroundColor: scheme.surface)` (cinza; era `surfaceContainerLowest`), **sem appBar**.
2. `body: CustomScrollView(slivers:[...])`:
   - `IosGlassHeader(title: 'Cliente', leading: BackButton(onPressed: canPop?pop:go('/clientes')), actions: [refresh → invalidate clienteDetailProvider + clienteOsHistoricoProvider])`.
   - `async.when`: loading → `SliverFillRemaining(Center(spinner))`; error → `SliverFillRemaining(Padding(AppStatePanel.error(...)))`; data → `SliverToBoxAdapter(_Body(cliente: c))`.
3. `_Body.build`: `ListView(padding: fromLTRB(16,12,16,24), children:[...])` → `Padding(padding: fromLTRB(16,12,16,24), child: Column(crossAxisAlignment: stretch, children:[...]))` — MESMOS filhos.

## Não muda
- Seções (Header/Endereço/Conexão/Instalação/Materiais/Observação/**Fotos**/Histórico), `ClienteFotosSection`, `ClienteMateriaisSection`, lógica/dados/providers.
- (A foto da instalação quebrada é bug de backend/infra — `CLIENTE_FOTOS_DIR` apontando p/ fora do volume — tratado à parte; o app renderiza certo.)

## Critérios de sucesso
1. Header de vidro "Cliente" com **voltar** (com fallback /clientes) + atualizar; conteúdo rola sob o vidro.
2. Fundo cinza, cards brancos; todas as seções iguais; loading/erro ok.
3. `IosGlassHeader` sem `leading` continua igual (OS lista/detalhe, Estoque, Clientes lista intactos).
4. `flutter analyze` limpo (deploy).
5. Visual on-device (claro/escuro): voltar funciona (inclusive via deep link), nada quebrado.

## Riscos
- `ListView`→`Column(stretch)` dentro de `SliverToBoxAdapter`: garantir stretch (cards full-width); sem `Expanded` nos filhos (não há).
- `leading` no `IosGlassHeader`: passar `automaticallyImplyLeading: showBackButton` junto (quando leading != null, o SliverAppBar usa o leading; quando null, cai no automaticallyImplyLeading).
