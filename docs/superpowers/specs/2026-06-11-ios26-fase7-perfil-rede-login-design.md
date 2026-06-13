# iOS 26 — Fase 7: Perfil + Rede + Login (reta final) — Design

**Data:** 2026-06-11 (ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Telas:** `perfil_screen.dart`, `rede/rede_screen.dart`, `auth/login_screen.dart`

## Objetivo
Fechar o iOS 26 nas 3 telas restantes, reusando os componentes já prontos
(`IosGlassHeader` sliver + `IosGlassAppBar`). Nenhum componente novo.

## Perfil (`perfil_screen.dart`) — tela-raiz
Hoje: `Scaffold(surface, AppBar(refresh), body: async.when(loading→_StateBody, error→_ErroView, data→RefreshIndicator(ListView[_Header, stats, seções Conta/Sobre])))`.
Vira: `RefreshIndicator`→`CustomScrollView(AlwaysScrollable, slivers:[ IosGlassHeader('Perfil', actions:[refresh]), ...async.when<List<Widget>>(loading→[SliverFillRemaining(_StateBody)], error→[SliverFillRemaining(_ErroView)], data(p)→[SliverPadding(bottom: 32+74+inset, sliver: SliverToBoxAdapter(child: Column(crossAxisAlignment: stretch, children:[<MESMOS filhos>])))]) ])`.
- Mantém a folga inferior (navbar flutuante). KPIs/stats/ações/logout/easter-egg intactos.

## Rede (`rede/rede_screen.dart`) — push (tem `cpf`)
Hoje: `Scaffold(AppBar('Rede do cliente', refresh), body: status.when(loading→spinner, error→Center, data→_body(s)))`; `_body` é `ListView(padding all 16, children:[...])`.
Vira: `Scaffold(surface, body: CustomScrollView(slivers:[ IosGlassHeader('Rede do cliente', showBackButton: true, actions:[refresh → invalida redeStatus+redeDiagnostico]), ...status.when<List<Widget>>(loading→[SliverFillRemaining(spinner)], error→[SliverFillRemaining(Center erro+retry)], data(s)→[SliverToBoxAdapter(child: _body(s))]) ]))`.
- `_body`: `ListView(...)` → `Padding(all 16, child: Column(crossAxisAlignment: stretch, children:[<MESMOS filhos>]))`. `_diagnostico()` e tudo mais intactos.

## Login (`auth/login_screen.dart`) — sem AppBar
Hoje: `Scaffold(backgroundColor: surfaceContainerLowest, body: SafeArea(SingleChildScrollView(Center(form + _AmbientGlow))))`.
Vira: **só** `backgroundColor: surfaceContainerLowest` → `scheme.surface`. Sem header (login não tem nav). Inputs/botões já herdam a Fase 0.

## Não muda
- Lógica/dados/providers de todas as 3; `_Header`/`_StatsGrid`/`_ActionTile`/`_InfoTile` (perfil), `_body`/`_diagnostico`/troca de senha WiFi (rede), `_entrar`/biometria/_AmbientGlow (login).

## Critérios de sucesso
1. Perfil: header de vidro "Perfil" + atualizar; conteúdo rola sob o vidro; folga do navbar preservada.
2. Rede: header de vidro "Rede do cliente" com **voltar** + atualizar; conteúdo rola sob o vidro.
3. Login: fundo cinza agrupado; form/inputs/botões iguais (Fase 0).
4. `flutter analyze` limpo (deploy).
5. Visual on-device (claro/escuro): nada quebrado nas 3.

## Riscos
- Perfil: `_StatsGrid` é GridView — confirmar que faz `shrinkWrap` (já está num ListView hoje, então sim) ao ir pro Column.
- Rede: `_body` é método de `_RedeScreenState` (não widget separado) — converter o `return ListView` p/ `Padding/Column(stretch)` com os MESMOS filhos; FilledButton full-width segue ok no Column(stretch).
- `status.when<List<Widget>>`/`async.when<List<Widget>>` + spread: tipo explícito nos branches.
- Sem teste automatizado (refactor visual; telas com provider/form). Validar via analyze + on-device.
