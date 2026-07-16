# Identidade Vibrante — Onda 8: 4ª rodada de QA do Robert

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Logo nova transparente no login (sem zoom); sheets bonitos pra "CPF já tem conta" e "esqueci a senha"; CTA "Quero ser cliente" abaixo do Continuar; layout do header da home refeito de forma robusta (desalinhamentos); contraste do "vencida há N dias" nas Faturas; investigação do erro do Pix.

## Global Constraints

- Diretório: `apps/cliente-mobile`. Commits direto na main, um por task. NÃO push. Gate: `flutter test` (17) + `flutter analyze lib test` grepado `error •|warning •` = zero (140 infos, não crescer).
- Asset novo já copiado pelo controller: `assets/icon/logo_marca.png` (1200px, RGBA transparente) — pasta `assets/icon/` já declarada no pubspec.
- Padrão de sheet (referência: sheet do CPF não encontrado em onboarding_cpf_screen.dart): rounded top radiusFolha, ícone 48, título titleLarge w900 centrado, corpo bodyMedium centrado, botões empilhados.

---

### Task 1: Login — logo nova sem zoom

**Files:** `lib/features/auth/login_screen.dart`

- [ ] Trocar a marca d'água: `Positioned.fill > IgnorePointer > Opacity` — remover `ClipRect`/`Transform.scale`; usar `Image.asset('assets/icon/logo_marca.png', fit: BoxFit.contain, alignment: Alignment.centerRight)` com `Opacity` 0.10 (transparência real do PNG novo; sem fundo, sem cortes). Se `contain` deixar pequena demais na vertical, usar `BoxFit.fitHeight`.
- [ ] Commit: `feat(cliente): logo nova transparente no login`. Incluir `assets/icon/logo_marca.png` no add.

### Task 2: Sheets bonitos — CPF já tem conta + esqueci a senha

**Files:** `lib/features/onboarding/onboarding_cpf_screen.dart`, `lib/features/auth/login_screen.dart`

- [ ] **409 (CPF já tem conta):** substituir o toast por sheet no padrão: ícone `Icons.celebration_rounded` 48 `BrandTokens.primary`; título `Você já tem conta!`; corpo `Esse CPF já está cadastrado. Bora entrar? Se esqueceu a senha, dá pra recuperar na tela de login.`; botão FilledButton primary `Ir pro login` → fecha e navega como hoje (mesma rota/extra com o CPF). Detectar 409 de forma tipada se trivial (statusCode no registerStart, como o notFound) — senão manter a detecção atual por mensagem, mas trocar a UI.
- [ ] **Esqueci a senha (login `_forgot`):** substituir o toast por sheet: ícone `Icons.mark_chat_read_rounded` 48 primary; título `Código a caminho!`; corpo `Se esse CPF estiver cadastrado, você vai receber um código no WhatsApp em instantes.`; botão `Continuar` → fecha e navega pro reset como hoje. Fluxo/timing idênticos (sheet ANTES do push, aguardar fechar).
- [ ] Commit: `feat(cliente): sheets acolhedores pra cpf com conta e esqueci a senha`.

### Task 3: CTA "Quero ser cliente" abaixo do Continuar

**Files:** `lib/features/onboarding/onboarding_cpf_screen.dart`

- [ ] Mover o bloco (`Ainda não é cliente?` + OutlinedButton verde) de baixo do card de confiança pro slot `bottom` do AuthScaffold, ABAIXO do botão Continuar existente (ordem: Continuar, espaçamento spaceSm, texto, botão). Conferir como o `bottom` é montado hoje e preservar o Continuar intacto.
- [ ] Commit: `fix(cliente): quero ser cliente abaixo do continuar`.

### Task 4: Home header — layout robusto (fim dos desalinhamentos)

**Files:** `lib/features/home/widgets/home_capa.dart`

- [ ] Refazer o conteúdo do `HomeCapaDelegate.build` abandonando o posicionamento absoluto por elemento (fonte dos desalinhamentos): **dois layouts naturais em cross-fade**:
  - `_ExpandedLayout`: `Column` com padding normal (saudação+sino / status block completo / linha contrato) — exatamente o visual pré-colapso, layout por flow (sem Positioned por elemento).
  - `_CollapsedLayout`: `Column` compacta centrada verticalmente na banda útil: linha status (pill + plano + chip Minha rede) + linha contrato compacta (11, clicável).
  - Stack: fundo (CapaBackground + FolhaLip) + `IgnorePointer(ignoring: t > 0.5, child: Opacity(opacity: (1 - t*2).clamp(0,1), child: _ExpandedLayout))` + `IgnorePointer(ignoring: t <= 0.5, child: Opacity(opacity: ((t - 0.5)*2).clamp(0,1), child: _CollapsedLayout))`.
  - Extents mantidos (com fontScale). Sem lerp de posição — os layouts são estáticos, só opacidade cruza. Alinhamento garantido por Column/Padding normais.
- [ ] Estados loading/error preservados. Interações: sino/minha rede/contrato clicáveis no layout visível.
- [ ] Commit: `fix(cliente): header da home com layouts em crossfade (fim dos desalinhamentos)`.

### Task 5: Faturas — contraste do vencida

**Files:** `lib/features/faturas/faturas_screen.dart`

- [ ] Localizar o hero da fatura aberta (`_AbertaHeroCard`): quando vencida, o fundo é gradiente vermelho e o texto "Vencida há N dias"/botão também vermelhos — ilegível. Fix: sobre fundo vermelho, textos/badges em branco (`Colors.white` / white70) e o botão Pagar com Pix em BRANCO com texto vermelho (`backgroundColor: Colors.white, foregroundColor: BrandTokens.danger`) — inverter o contraste. Estados não-vencidos inalterados.
- [ ] Commit: `fix(cliente): contraste do estado vencida no hero de faturas`.

### Task 6: Investigar "não conseguimos gerar o pix agora"

**Files:** leitura em `lib/` e `apps/api` (fix SÓ se for bug claro no app; senão relatório)

- [ ] Rastrear o fluxo: botão Pagar com Pix → repositório Flutter → endpoint da API → integração SGP. Identificar onde a mensagem `não conseguimos gerar o pix` nasce e as causas possíveis (ex: SGP não gera pix pra fatura vencida? timeout? campo faltando?). NÃO mexer em backend sem certeza — se a causa for externa (SGP/prod), documentar num relatório com o diagnóstico e o que checar em prod (logs, resposta do SGP).
- [ ] Se for bug claro e local (ex: parsing, campo errado), corrigir + gates + commit `fix(...)`. Senão, sem commit — só o relatório.

### Task 7: Verificação da onda

- [ ] Gates + `flutter build apk --debug`.
- [ ] Review whole-branch (base = commit anterior à T1).
- [ ] Checklist manual (Robert): logo nova, sheets (409/esqueci), CTA abaixo do Continuar, home alinhada (expandida/colapsada/scroll), faturas vencida legível. WhatsApp CTA: precisa do deploy da API (onda 6).
