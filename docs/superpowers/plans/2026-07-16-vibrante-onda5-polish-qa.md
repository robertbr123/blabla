# Identidade Vibrante — Onda 5: polish pós-QA do Robert

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir o crash do widget iOS e aplicar os ajustes do teste em aparelho: capa das Faturas rasa, contraste das tabs do Suporte, header do Perfil com colapso ao rolar, splash na identidade nova, onboarding CPF mais rico, e o hero do login com "Onde" maiúsculo + logo marca d'água + palavra rotativa animada.

**Architecture:** Ajustes pontuais por tela. Única mudança estrutural: o Perfil troca Column+folha por `CustomScrollView` com `SliverPersistentHeader` pinned (capa colapsa de avatar grande+nome+plano pra mini avatar+nome fixos).

**Tech Stack:** Flutter; `CapaBackground`/`FolhaContainer`/tokens existentes; `assets/icon/icon.png` (único asset de logo disponível).

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO dar push. NUNCA `git add -A` (WIP em conexao_screen.dart).
- Gate por task: `flutter test` verde (17) + `flutter analyze lib test` — o IMPLEMENTER deve grepar a saída completa por `error •|warning •` (zero matches) e reportar a contagem de infos (~147 baseline); nunca `flutter analyze` puro.
- Lógica/providers/navegação intactos em todas as tasks (exceto onde o ajuste É de comportamento visual, ex: colapso do perfil).
- Ler cada arquivo inteiro antes de editar.

---

### Task 1: Bugfix — widget de home screen crasha no iOS

**Files:**
- Modify: `lib/core/widget/home_widget_service.dart`

**Contexto:** `HomeWidget.saveWidgetData` lança `PlatformException(-7, AppGroupId not set)` no iOS. O `refresh()` já tem guard `if (!Platform.isAndroid) return;` — os saves não.

- [ ] Em `setStatus` e `setProximaFatura`, adicionar `if (!Platform.isAndroid) return;` como primeira linha (widget iOS/WidgetKit é onda futura — comentário do arquivo já diz isso; atualizar o doc comment da classe pra refletir que iOS agora é no-op). Conferir se `sync()` chama só esses três (se chamar saves direto, mesmo guard).
- [ ] Gates + commit: `fix(cliente): widget home screen no-op fora do Android (crash AppGroupId no iOS)`.

### Task 2: Login — "Onde" maiúsculo, logo marca d'água e palavra rotativa

**Files:**
- Modify: `lib/features/auth/login_screen.dart`
- Modify: `pubspec.yaml` (só se precisar declarar asset — `assets/icon/` já está declarado)

- [ ] **Título:** `Onde\nvocê\n<palavra>` — "Onde" com O maiúsculo (referência à Ondeline). A terceira linha vira um widget `_PalavraRotativa`: lista `['estiver.', 'morar.', 'trabalhar.', 'estudar.', 'precisar.']`, `Timer.periodic` de 2600ms trocando o índice, `AnimatedSwitcher` (duração 400ms) com transição fade + slide vertical leve (`SlideTransition` de `Offset(0, 0.35)` → zero). Mesma `TextStyle` do displayTitle. Timer cancelado no dispose. `Text` com `key: ValueKey(palavra)` pro switcher animar.
- [ ] **Logo marca d'água:** dentro da capa, `Positioned`/`Align` com `assets/icon/icon.png` grande (~220px) no canto direito, atravessando o degradê: `Opacity(0.10)` + `ShaderMask`/fade suave se trivial (senão só opacity). Usar `Image.asset('assets/icon/icon.png')`. Não pode atrapalhar a leitura do título nem os toques.
- [ ] Nada mais muda (form, biometria, handlers intactos).
- [ ] Gates + commit: `feat(cliente): login — Onde maiusculo, logo marca dagua e palavra rotativa`.

### Task 3: Faturas capa com corpo + Suporte contraste das tabs

**Files:**
- Modify: `lib/features/faturas/faturas_screen.dart`
- Modify: `lib/features/suporte/suporte_screen.dart`

- [ ] **Faturas:** a capa (título só) ficou rasa ("um pedacinho azul"). Dar corpo: subtítulo abaixo do título — `Suas contas e pagamentos num só lugar.` em `capaInk` 70% (13, w600) — e aumentar o respiro do título (padding top da capa +spaceMd). Usar o `capaBottom`?? NÃO — o subtítulo entra via `capaBottom` do CapaPageScaffold (é exatamente o slot pra isso; ele reduz o padding inferior — se visualmente ficar apertado, adicionar `SizedBox` interno).
- [ ] **Suporte:** `unselectedLabelColor` das tabs passa de `capaInk 55%` pra `Colors.white.withValues(alpha: 0.75)` (legibilidade sobre o ciano). Manter selecionada branca + indicator branco.
- [ ] Gates + commit: `fix(cliente): capa das faturas com subtitulo e contraste das tabs do suporte`.

### Task 4: Perfil — header que colapsa (avatar+nome fixos ao rolar) e fim do corte azul

**Files:**
- Modify: `lib/features/perfil/perfil_screen.dart`

- [ ] Substituir a estrutura Column[capa, Expanded(folha)] por `CustomScrollView`:
  - `SliverPersistentHeader(pinned: true, delegate: _PerfilCapaDelegate)`: maxExtent ≈ `topInset + 210`, minExtent = `topInset + 64`. Expandido: avatar 72 + nome em `displayGreeting` + plano (como hoje). Colapsado: linha com avatar 28 + nome (16, w800, capaInk), plano some. Interpolar tamanhos/opacidades com `shrinkOffset/(maxExtent-minExtent)` clamped. Fundo do header: `CapaBackground` (gradiente + onda) preenchendo todo o extent.
  - Conteúdo: `SliverToBoxAdapter` com a técnica do canto: um `Container` com o fim do gradiente da capa (`BrandTokens.capaDeep`) atrás e, dentro, o container da folha com cantos superiores `radiusFolha` — assim não aparece "corte azul"/fresta entre capa e folha em nenhuma posição de scroll. O resto da lista (opções, logout etc.) vem dentro, intacto.
  - Estados loading/error do meProvider continuam com skeleton/fallback equivalentes (skeleton = header expandido com spinner).
- [ ] Atenção dark mode: cor da folha via tema como hoje.
- [ ] Gates + commit: `feat(cliente): perfil com header colapsavel fixo ao rolar`.

### Task 5: Splash na identidade nova

**Files:**
- Modify: `lib/features/splash/splash_screen.dart`

- [ ] Trocar `AnimatedGradientBackground`/`primaryDark` pela capa vibrante: `Container` com `BrandTokens.gradientCapa` + o card branco do logo existente no centro (mantém `assets/icon/icon.png` e as animações scale/fade atuais) + tagline `Ondeline — internet que acompanha você.` embaixo do logo em `capaInk` 70% (13, w600). A onda decorativa: reutilizar `CapaBackground` como fundo (ele já desenha as ondas). Lógica `_decide()` (token/biometria/rotas) INTACTA.
- [ ] Se `AnimatedGradientBackground` ficar sem NENHUMA referência em lib/ depois disso, deletar o arquivo.
- [ ] Gates + commit: `feat(cliente): splash na identidade vibrante`.

### Task 6: Onboarding CPF mais acolhedor

**Files:**
- Modify: `lib/features/onboarding/onboarding_cpf_screen.dart`

- [ ] Enriquecer sem inventar features: título vira `Vamos te encontrar` mantido, subtítulo mais quente: `Digite o CPF do titular do contrato pra gente localizar seu cadastro.` Abaixo do campo, um card informativo leve (surface, radius 16, ícone `Icons.verified_user_outlined` em `BrandTokens.primary`): título `Por que pedimos seu CPF?` (13, w800) e texto `Usamos só pra localizar seu contrato na Ondeline. Seus dados ficam protegidos.` (12, textSecondary). CTA e validação intactos.
- [ ] Gates + commit: `feat(cliente): onboarding cpf mais acolhedor`.

### Task 7: Verificação da onda

- [ ] `flutter test` + `flutter analyze lib test` (0 err/warn via grep) + `flutter build apk --debug`.
- [ ] Review whole-branch da onda (base = commit anterior à Task 1), atenção: timer da palavra rotativa (leak/dispose), delegate do perfil (shouldRebuild), guard iOS do widget, splash sem regressão de fluxo.
- [ ] Checklist manual (Robert): rodar no iPhone — sem crash de widget; login com animação; faturas/suporte/perfil; splash; criar conta.
