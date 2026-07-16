# Identidade Vibrante — Onda 4: telas restantes + onboarding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a identidade "Vibrante de marca" no app inteiro: migrar as 8 telas restantes com GlassAppBar pro `CapaPageScaffold` e dar ao onboarding (4 telas via `AuthScaffold`) o mesmo tratamento do login.

**Architecture:** Tasks 1–4 são migrações mecânicas pro `CapaPageScaffold` (padrão da Onda 3). Task 5 reescreve o `AuthScaffold` internamente pra capa+folha (as 4 telas de onboarding herdam sem mudar de API) e troca campos/botões glass pelos da identidade nova nas telas filhas. Task 6 verifica e faz o review da onda.

**Tech Stack:** `CapaPageScaffold`, `CapaBackground`/`FolhaContainer`, `SheetTextField`, tokens `BrandTokens`.

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO dar push.
- FORA da onda: `conexao_screen.dart` (WIP do Robert) e `promocao_detalhe_screen.dart` (SliverAppBar com imagem do promo é design intencional).
- ZERO mudança de lógica/providers/navegação/validação; só casca + remoção de compensações do header antigo (top padding do scroll → `BrandTokens.spaceLg`).
- Telas empurradas: `CapaPageScaffold` (nunca capa manual); actions SEM cor explícita (IconTheme cuida).
- Gate por task: `flutter test` verde (17) + `flutter analyze lib test` ZERO errors/warnings, sem issues novas (~157 infos pré-existentes; nunca `flutter analyze` puro). NUNCA `git add -A`.
- Ler cada arquivo INTEIRO antes de editar.

---

### Task 1: Editar perfil + Mudar senha

**Files:**
- Modify: `lib/features/perfil/editar_perfil_screen.dart` (123L)
- Modify: `lib/features/perfil/mudar_senha_screen.dart` (116L)

- [ ] Migrar ambas pro `CapaPageScaffold` (títulos atuais dos GlassAppBar mantidos), remover compensações. Formularios/validação intactos (teclado ok por construção — scroll dentro da folha).
- [ ] Gates + commit único: `feat(cliente): editar perfil e mudar senha com capa vibrante`.

### Task 2: FAQ (lista + artigo)

**Files:**
- Modify: `lib/features/faq/faq_screen.dart` (268L)
- Modify: `lib/features/faq/faq_artigo_screen.dart` (174L)

- [ ] Migrar ambas pro `CapaPageScaffold` (títulos mantidos; busca/campo de filtro do FAQ, se houver, fica na folha ou vai pro `capaBottom` SE for mudança trivial de casca). Conteúdo/markdown do artigo intacto.
- [ ] Gates + commit único: `feat(cliente): faq com capa vibrante`.

### Task 3: Contatos + Legal + Promoções

**Files:**
- Modify: `lib/features/contatos/contatos_screen.dart` (268L)
- Modify: `lib/features/legal/legal_screen.dart` (107L)
- Modify: `lib/features/promocoes/promocoes_screen.dart` (94L)

- [ ] Migrar as três pro `CapaPageScaffold` (títulos mantidos), remover compensações. Links de contato (WhatsApp/Instagram/etc), textos legais e lista de promoções intactos.
- [ ] Gates + commit único: `feat(cliente): contatos, legal e promocoes com capa vibrante`.

### Task 4: Indicação

**Files:**
- Modify: `lib/features/indicacao/indicacao_screen.dart` (814L)

- [ ] Tela grande — ler com calma. Migrar pro `CapaPageScaffold` (título mantido), remover compensações. Fluxo de indicação (código, share, recompensas F10) intacto.
- [ ] Gates + commit: `feat(cliente): indicacao com capa vibrante`.

### Task 5: Onboarding — AuthScaffold vibrante

**Files:**
- Modify: `lib/core/ui/auth_scaffold.dart`
- Modify: `lib/features/onboarding/onboarding_cpf_screen.dart` (119L)
- Modify: `lib/features/onboarding/onboarding_otp_screen.dart` (118L)
- Modify: `lib/features/onboarding/onboarding_password_screen.dart` (160L)
- Modify: `lib/features/onboarding/onboarding_biometric_screen.dart` (102L)

- [ ] **AuthScaffold:** manter a API (`title`, `subtitle`, `child`, `icon`, `showBack`, `bottom`) e reescrever o build pro padrão do reset de senha: capa (`CapaBackground`) com voltar (quando `showBack`, `Icons.arrow_back_rounded` em `capaInk`) + título (`TextStyle(color: capaInk, fontSize: 24, fontWeight: w900, letterSpacing: -0.6)`) + subtítulo (`capaInk` 70%, 13, w600); o `icon` some do header (a capa não usa ícone — se alguma tela depender visualmente dele, ignora: o param fica aceito e não renderizado, com comentário). Depois `Expanded(SingleChildScrollView(FolhaContainer(overlap: radiusFolha, padding: spaceLg, child: child)))` e o `bottom` (CTAs) dentro da folha após o child (manter como está estruturado hoje — child no meio, bottom no rodapé — adaptando pro scroll da folha). `GestureDetector` de unfocus mantido.
- [ ] **Telas filhas:** trocar `GlassTextField` → `SheetTextField` (lib/core/ui/sheet_text_field.dart — API: controller, label, keyboardType, inputFormatters, obscureText, prefixIcon: IconData?, suffix) e `GlassPrimaryButton` → `FilledButton` ciano do padrão login (minimumSize Size.fromHeight(52), radiusMd, w800 16, spinner branco quando loading). Textos/validações/handlers intactos. Elementos glass secundários (chips de reenviar código etc.): adaptar cores pra folha clara (textPrimary/textSecondary) sem mudar comportamento.
- [ ] Gates + commit único: `feat(cliente): onboarding com capa vibrante + folha`.

### Task 6: Verificação da onda + limpeza

- [ ] `flutter test` verde + `flutter analyze lib test` (0 err/warn) + `flutter build apk --debug` ok.
- [ ] Limpeza de mortos: se `AnimatedGradientBackground` e/ou `glass_card.dart` (GlassTextField/GlassPrimaryButton/GlassCard) ficarem sem NENHUMA referência em lib/, deletar arquivo + testes correspondentes. `glass_app_bar.dart` NÃO deletar (conexao_screen WIP ainda usa) — anotar. Splash ainda usa AnimatedGradientBackground? Verificar antes (grep) — se usar, mantém.
- [ ] Review whole-branch da onda (base = commit anterior à Task 1).
- [ ] Checklist manual (Robert): fluxo de criar conta completo (CPF → OTP → senha → biometria), FAQ, indicação, promoções, contatos, legal, editar perfil/senha; dark mode.
