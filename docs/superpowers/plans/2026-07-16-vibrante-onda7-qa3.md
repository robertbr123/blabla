# Identidade Vibrante — Onda 7: 3ª rodada de QA do Robert

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Logo do login com zoom (sem borda cortada aparente), Faturas com header colapsável igual perfil, contrato visível na home colapsada, e CTA "Quero ser cliente" fixo na tela do CPF (sem o chip Passo 1 de 3).

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO push. Gate: `flutter test` (17) + `flutter analyze lib test` grepado `error •|warning •` = zero (140 infos, não crescer).
- Padrões de referência: `_PerfilCapaDelegate` (perfil_screen.dart) e `HomeCapaDelegate` (home_capa.dart) — lip via FolhaLip, fontScale clamp 1.2, valores via construtor, shouldRebuild.

---

### Task 1: Login — logo com zoom (sem cortes visíveis)

**Files:** `lib/features/auth/login_screen.dart`

- [ ] O `Positioned.fill` da marca d'água ganha zoom pra que as bordas da imagem saiam da tela (a imagem tem fundo/borda visível quando encostada na borda): envolver o `Image.asset` em `Transform.scale(scale: 1.45)` (dentro do Opacity, com `ClipRect` garantido pelo próprio Positioned.fill + adicionar `ClipRect` se necessário pra não vazar pra folha), manter `BoxFit.cover` + `alignment: Alignment.center`. Resultado: logo grande atravessando a capa, nenhuma aresta da imagem visível.
- [ ] Gates + commit: `fix(cliente): logo do login com zoom, sem borda cortada`.

### Task 2: Faturas — header colapsável (igual perfil)

**Files:** `lib/features/faturas/faturas_screen.dart`

- [ ] Substituir a capa estática por `CustomScrollView` + `SliverPersistentHeader(pinned: true, delegate: _FaturasCapaDelegate)` no padrão dos delegates existentes (fontScale clamp incluído): expandido = título `Faturas` (24/w900/capaInk) + subtítulo atual; colapsado = só o título (18/w900) centrado verticalmente na banda; FolhaLip no bottom. maxExtent ≈ topInset + 120*fontScale; minExtent ≈ topInset + (56 + radiusFolha)*fontScale.
- [ ] O conteúdo (lista com filtro de ano, cards, refresh) vira `SliverToBoxAdapter` com container plano cor da folha (bottom 120 mantido). `RefreshIndicator` com edgeOffset = maxExtent. ZERO mudança na lógica/cards.
- [ ] Gates + commit: `feat(cliente): faturas com header colapsavel`.

### Task 3: Home colapsada mostra o contrato

**Files:** `lib/features/home/widgets/home_capa.dart`

- [ ] No estado colapsado do `HomeCapaDelegate`, a linha do contrato (endereço + troca quando multi-contrato) NÃO some mais: vira uma linha compacta (fontSize ~11, capaInk 70%, ícone 12) logo abaixo da barra compacta de status, clicável pra `showContratoSelector` quando `podeTrocarContrato`. Ajustar minExtent (+ ~20*fontScale) e as posições/lerps pra acomodar sem colisão com o lip. Estado expandido inalterado.
- [ ] Gates + commit: `feat(cliente): contrato visivel e trocavel na home colapsada`.

### Task 4: CPF — sem "Passo 1 de 3" + CTA fixo "Quero ser cliente"

**Files:** `lib/features/onboarding/onboarding_cpf_screen.dart`

- [ ] Remover o chip `Passo 1 de 3`.
- [ ] Abaixo do card "Por que pedimos seu CPF?", adicionar CTA permanente: divisor visual leve + `Ainda não é cliente?` (12, textSecondary, centrado) + `OutlinedButton.icon` verde WhatsApp (borda `BrandTokens.brandWhatsapp`, foreground brandWhatsapp, height 48, radiusMd, icon `Icons.chat_rounded`, label `Quero ser cliente`) → mesma ação do sheet: busca contato whatsapp via `contatosOperadoraProvider` (best-effort, try/catch) e abre wa.me com a mensagem padrão; sem número → toast `Não conseguimos abrir o WhatsApp agora. Tenta de novo mais tarde.` Extrair a lógica de abrir-whatsapp num helper privado reutilizado pelo sheet e pelo CTA (sem duplicar).
- [ ] O bottom sheet de CPF não encontrado permanece como está.
- [ ] Gates + commit: `feat(cliente): CTA quero ser cliente fixo na tela de cpf`.

### Task 5: Verificação da onda

- [ ] `flutter test` + `flutter analyze lib test` (grep 0) + `flutter build apk --debug`.
- [ ] Review whole-branch (base = commit anterior à T1): delegates novos (faturas), colisões de geometria (home minExtent novo), helper whatsapp único.
- [ ] Checklist manual (Robert): logo sem cortes, faturas colapsando, contrato na home colapsada, CTA na tela do CPF.
