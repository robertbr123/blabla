# iOS 26 — Fase 6: Cliente cadastro — Design

**Data:** 2026-06-11 (ciclo iOS 26)
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/clientes/cliente_novo_screen.dart` (push; form Stepper 3 passos)

## Contexto / restrição técnica
O cadastro usa `Stepper` Material dentro de `Column`+`Expanded` (Stepper rola por dentro). Isso NÃO combina com `CustomScrollView`/sliver, então o `IosGlassHeader` (sliver) não serve. Solução: um **AppBar de vidro não-sliver** (`PreferredSizeWidget`), reutilizável por telas de form (cadastro, Rede, Login).

## Componente novo
`IosGlassAppBar` (`lib/core/ui/ios_glass_app_bar.dart`) — `StatelessWidget implements PreferredSizeWidget`:
- `preferredSize => Size.fromHeight(kToolbarHeight)`.
- build: `ClipRect`→`BackdropFilter(blur ~18)`→`AppBar(backgroundColor: surface.withAlpha(0.7), surfaceTint transparent, elevation 0, scrolledUnderElevation 0, title estilo 20/w800/onSurface, titleSpacing 16, automaticallyImplyLeading: showBackButton, leading, actions)`.
- API: `IosGlassAppBar({required String title, List<Widget> actions = const [], Widget? leading, bool showBackButton = true})`.
- Nota honesta: sem `extendBodyBehindAppBar` o blur é sutil (não há conteúdo rolando atrás); o ganho real é a translucidez + título padronizados + consistência. Irmão não-sliver do `IosGlassHeader`.

## Mudanças no cadastro (`cliente_novo_screen.dart`)
1. `Scaffold.backgroundColor`: `surfaceContainerLowest` → `scheme.surface`.
2. `appBar: AppBar(title: const Text('Novo cliente'), actions: [GPS chip])` → `appBar: IosGlassAppBar(title: 'Novo cliente', actions: [<mesmo chip GPS>])`.
3. Resto inalterado: card "Cadastro guiado", chips de etapa/GPS, `Stepper`, campos, validações.

## Não muda
- Stepper, validações, ViaCEP, GPS (`_gps`/`_gpsCapturing`/`_capturarGps`), materiais, `_enviar`, navegação, dados.

## Critérios de sucesso
1. Cadastro com `IosGlassAppBar` "Novo cliente" (voltar + chip GPS), fundo cinza agrupado.
2. Form/Stepper/validações funcionam idênticos; inputs/botões já arredondados (Fase 0).
3. `IosGlassAppBar` reutilizável (sem acoplamento ao cadastro) — pronto p/ Rede/Login.
4. `flutter analyze` limpo (deploy).
5. Visual on-device (claro/escuro): barra translúcida consistente, nada quebrado.

## Riscos
- `BackdropFilter` envolvendo `AppBar` como `PreferredSizeWidget`: renderiza ok; blur é no-op visual sem `extendBodyBehindAppBar` (aceito — translucidez/título é o ganho).
- Título do AppBar: estilo explícito (20/w800) sobrepõe o `appBarTheme` (18/w600) — proposital, p/ casar com o `IosGlassHeader`.
