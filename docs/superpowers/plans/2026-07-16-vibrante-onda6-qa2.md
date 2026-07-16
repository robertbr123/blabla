# Identidade Vibrante — Onda 6: 2ª rodada de QA do Robert

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Transição do login mais bonita + logo full-bleed; padrão "lábio" (do perfil) nas capas de Faturas/Suporte/telas empurradas (bordas + fundo 100%); home com header colapsável tipo perfil; onboarding CPF bonito com mensagens melhores e CTA de WhatsApp pra virar cliente (com endpoint público novo).

## Global Constraints

- Diretório: `apps/cliente-mobile` (T4 toca `apps/api`). Commits direto na main, um por task. NÃO push. NUNCA `git add -A` (WIP em conexao_screen.dart).
- Gate Flutter por task: `flutter test` verde + `flutter analyze lib test` grepado por `error •|warning •` (zero; 140 infos baseline, não crescer).
- Gate API (T4): `ruff check . && ruff format --check .` em apps/api se disponível local; pytest NÃO roda local (CI valida pós-push) — anotar isso no report.
- Padrão "lábio" (referência: perfil pós-onda 5): o canto arredondado da folha é pintado DENTRO da capa (Positioned bottom, height radiusFolha, cor da folha theme-aware, BorderRadius.vertical top) e o conteúdo abaixo é container PLANO na cor da folha preenchendo todo o resto (Expanded) — nunca Transform/overlap.

---

### Task 1: Login — transição elegante + logo full-bleed

**Files:** `lib/features/auth/login_screen.dart`

- [ ] **Transição da `_PalavraRotativa`:** trocar por animação direcional com curvas: palavra nova entra de baixo (Offset(0, 0.6)→0) com fade, palavra antiga sai POR CIMA (0→Offset(0, -0.6)) com fade — usar `AnimatedSwitcher.layoutBuilder` (Stack alinhado à esquerda) + `transitionBuilder` que diferencia in/out via `animation.status`/two tweens (padrão: `SlideTransition(position: Tween(begin: Offset(0, 0.6), end: Offset.zero).chain(CurveTween(curve: Curves.easeOutCubic)).animate(animation))` — o widget que sai roda a mesma animation revertida, então o out naturalmente desce; pra sair pra CIMA usar `switchOutCurve` + tween custom: implementar com `DualTransitionBuilder` ou aceitar saída descendo se o visual ficar limpo — critério: sem sobreposição feia, movimento contínuo). Duração 450ms, intervalo 2800ms. `ClipRect` mantido.
- [ ] **Logo full-bleed:** a marca d'água passa a preencher a capa inteira: `Positioned.fill(child: IgnorePointer(child: Opacity(opacity: 0.08, child: Image.asset('assets/icon/icon.png', fit: BoxFit.cover, alignment: Alignment.centerRight))))`.
- [ ] Gates + commit: `feat(cliente): transicao elegante da palavra e logo full-bleed no login`.

### Task 2: Padrão lábio em Faturas, Suporte e CapaPageScaffold

**Files:** `lib/core/ui/capa_folha.dart`, `lib/core/ui/capa_page_scaffold.dart`, `lib/features/faturas/faturas_screen.dart`, `lib/features/suporte/suporte_screen.dart`

- [ ] Em `capa_folha.dart`: criar `class FolhaLip extends StatelessWidget` (Container height radiusFolha, cor folha theme-aware, radius vertical top) exportado pra reuso.
- [ ] `CapaPageScaffold`: capa vira Stack com `FolhaLip` em Positioned bottom (padding inferior da capa segue reservando o espaço); o `Expanded(FolhaContainer(overlap))` vira `Expanded(Container(color: folha theme-aware, child: ...))` — sem Transform. Testes existentes do scaffold continuam passando (não asseguram overlap).
- [ ] Faturas e Suporte (capas manuais): mesmo padrão — Stack com FolhaLip na capa; conteúdo abaixo em Container plano na cor da folha ocupando todo o Expanded (mata o "fundo não preenchido" e dá as bordas iguais ao perfil). Suporte: FAB/Stack externo preservado.
- [ ] Perfil NÃO muda (já usa o padrão). Login/reset/AuthScaffold NÃO mudam (folha ancorada em scroll, sem seam).
- [ ] Gates + commit: `fix(cliente): padrao labio da folha em faturas, suporte e telas empurradas`.

### Task 3: Home com header colapsável (igual perfil)

**Files:** `lib/features/home/home_screen.dart`, `lib/features/home/widgets/home_capa.dart`

- [ ] Estrutura: `CustomScrollView` + `SliverPersistentHeader(pinned: true, delegate: _HomeCapaDelegate)`. maxExtent ≈ topInset + altura atual da capa expandida (medir: saudação+sino+status block+linha contrato ≈ 230–250); minExtent = topInset + ~88 (status block compacto).
  - Expandido: como hoje (saudação, sino, bloco status completo com rede, linha contrato).
  - Colapsado: nome/saudação e sino somem (fade com t), fica FIXO o bloco de status compacto: linha única `● Conexão ativa · Fibra 600 Mega` + chip `Minha rede →` (dados já disponíveis). Linha de contrato some.
  - `FolhaLip` no bottom do header (padrão lábio).
- [ ] O restante da home (breaking bar, FaturaCard, ações rápidas, etc.) vira slivers (`SliverToBoxAdapter`/`SliverPadding` com Column) sobre container plano cor da folha; bottom padding 120 preservado. `RefreshIndicator` continua envolvendo o scroll (edgeOffset = maxExtent do header). NPS listen, pull-to-refresh (todas invalidações), `_persistMe`, estados loading/error (skeleton = header expandido) preservados.
- [ ] `HomeCapa` widget atual é absorvido/adaptado pelo delegate (pode virar builders internos; manter `saudacao()` e provider usage).
- [ ] Gates + commit: `feat(cliente): home com header colapsavel fixo ao rolar`.

### Task 4: API — contatos da operadora públicos + repo pré-login

**Files:** `apps/api/src/ondeline_api/api/v1/cliente_app_contatos.py`, teste correspondente em `apps/api/tests/`, `apps/cliente-mobile/lib/core/api/contatos_repository.dart`

- [ ] API: remover a dependência `get_current_cliente_user` do `GET` de listagem do router cliente (contatos da operadora são informação pública: telefone/WhatsApp/redes). Admin router intacto. Atualizar/adicionar teste: GET sem token → 200.
- [ ] Flutter: `ContatosRepository.list()` ganha `options: Options(extra: const {'skipAuth': true})` (verificar o nome exato da flag no api_client — mesma usada no auth_repository) pra funcionar pré-login sem anexar token.
- [ ] Gates Flutter + ruff em apps/api (pytest fica pro CI — anotar). Commit: `feat(api+cliente): contatos da operadora publicos pro fluxo pre-login`.

### Task 5: Onboarding CPF — visual caprichado + mensagens + CTA WhatsApp

**Files:** `lib/core/auth/auth_state.dart` (ou onde `RegisterStartResult` mora), `lib/core/auth/auth_repository.dart`, `lib/features/onboarding/onboarding_cpf_screen.dart`, `lib/features/onboarding/onboarding_otp_screen.dart`

- [ ] **Result tipado:** `RegisterStartResult` ganha caso `notFound` (mapear `statusCode == 404` no `registerStart` antes do error genérico).
- [ ] **Visual da tela CPF:** acima do campo, hero: círculo 88px com `gradientPrimary` + ícone `Icons.person_search_rounded` branco 44; chip `Passo 1 de 3` (pill pequena, surface, textSecondary) acima do título. Card "Por que pedimos seu CPF?" mantido. Respiro generoso.
- [ ] **CPF não encontrado (404):** em vez de toast, `showModalBottomSheet` acolhedor: ícone busca, título `Não achamos esse CPF`, texto `Confere se digitou certinho. Ainda não é cliente Ondeline? Bora resolver isso agora 😉`, botões: `Tentar de novo` (fecha) e `Quero ser cliente` (FilledButton verde WhatsApp `BrandTokens.brandWhatsapp` com ícone) → busca `contatosOperadoraProvider` (agora público), acha o contato tipo whatsapp e abre `https://wa.me/<num>?text=<'Olá! Baixei o app da Ondeline e quero ser cliente 😃'>` via url_launcher (encode). Sem contato whatsapp/configurado ou erro → botão some (graceful) e texto vira só a mensagem.
- [ ] **CPF encontrado:** tela OTP mais celebratória: título `Achamos seu cadastro! 🎉` e subtítulo `Enviamos um código pro seu WhatsApp <maskedPhone>. Digita ele aqui embaixo.` (maskedPhone já chega via extra — conferir). Lógica intacta.
- [ ] Gates + commit: `feat(cliente): onboarding cpf caprichado + mensagens e CTA whatsapp pra virar cliente`.

### Task 6: Verificação da onda

- [ ] `flutter test` + `flutter analyze lib test` (grep 0 err/warn) + `flutter build apk --debug`.
- [ ] Review whole-branch (base = commit anterior à T1): delegate da home (perf/estados), lábio consistente nas 6+ telas, fluxo CPF (404/409/ok), endpoint público (segurança: só leitura de dados públicos), transição do login.
- [ ] Checklist manual (Robert): login (transição + logo), faturas/suporte (bordas + fundo), home colapsando, CPF errado → sheet WhatsApp, CPF certo → OTP festivo. Lembrete: mudança de API precisa de deploy (push) pra funcionar no app.
