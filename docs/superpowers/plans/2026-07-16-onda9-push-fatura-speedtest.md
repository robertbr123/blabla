# Onda 9 — Lembretes de fatura por push + Speedtest in-app

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** (1) Push no app lembrando fatura: 3 dias antes (D-3) e no dia do vencimento (D0), plugado na régua de cobrança existente, com opt-out nas preferências. (2) Speedtest in-app na tela de Conexão (medindo contra a Cloudflare), junto com a migração dela pro visual vibrante.

**Decisões do Robert:** timing D-3 + D0; speedtest contra CDN público Cloudflare.

## Global Constraints

- Monorepo: `apps/api` (T1) + `apps/cliente-mobile` (T2, T3). Commits direto na main, um por task. NÃO push.
- **A régua de WhatsApp está EM PRODUÇÃO — mudanças na `cobranca_regua.py` devem ser ADITIVAS e mínimas** (não alterar textos/gatilhos/fluxo WhatsApp existentes). Nada de renomear/mover funções usadas.
- Gate Flutter: `flutter test` verde + `flutter analyze lib test` grepado `error •|warning •` = zero (~125 infos, não crescer). Gate API: `ruff check` + `ruff format --check` limpos nos arquivos tocados; pytest fica pro CI (anotar no report). CI gotcha: task Celery NOVA precisa entrar no `include` do celery_app (se criar task nova).
- Ler cada arquivo inteiro antes de editar.

---

### Task 1 (API): push de fatura D-3 e D0 via régua

**Files:** `apps/api/src/ondeline_api/services/cobranca_regua.py`, `apps/api/src/ondeline_api/services/cliente_app_notif.py` (leitura/uso), teste novo em `apps/api/tests/`

- [ ] Ler inteiros: `cobranca_regua.py` (gatilhos, dedup/idempotência existente, como itera clientes), `cliente_app_notif.py` (assinatura pra criar notificação in-app+push, categorias), modelo `ClienteAppNotifPrefs` (categorias JSONB) e como o app resolve categoria→toggle (endpoint de prefs).
- [ ] **D-3 (gatilho existente):** no ponto onde a régua dispara o WhatsApp de D-3, ADICIONAR (sem alterar o fluxo atual) o envio de notificação do app pro `cliente_app_user` vinculado ao cliente (se existir): categoria `faturas` (nova — default ligado pra quem não tem pref explícita), título `Sua fatura vence em 3 dias 💡`, corpo `R$ {valor} até {dd/MM}. Pague pelo app com Pix em segundos.` Usa o mesmo mecanismo de idempotência da régua (mesma chave/registro com sufixo do canal) pra nunca duplicar.
- [ ] **D0 (gatilho novo, push-only):** adicionar `0` à estrutura de gatilhos SÓ pro canal app-push (NÃO WhatsApp): título `Sua fatura vence hoje ⚠️`, corpo `R$ {valor} vence hoje. Evite bloqueio — pague com Pix pelo app.` Mesma idempotência.
- [ ] Respeitar a pref: se o user desligou a categoria `faturas` nas prefs, não envia push (o serviço `cliente_app_notif` pode já fazer isso — conferir; senão, checar antes de enviar).
- [ ] Teste: unit/e2e no estilo dos testes existentes da régua cobrindo: D-3 gera notificação app; D0 gera; idempotência (rodar 2x não duplica); pref desligada não gera. `ruff check`/`format --check` limpos. pytest → CI.
- [ ] Commit: `feat(api): lembretes de fatura no push do app (D-3 e D0) via regua`.

### Task 2 (app): tela Conexão no visual vibrante

**Files:** `apps/cliente-mobile/lib/features/conexao/conexao_screen.dart`

- [ ] Última tela no estilo antigo (WIP do Robert já commitado — arquivo liberado). Ler inteira e migrar pro `CapaPageScaffold` (título atual do GlassAppBar), removendo compensações de header (top → `BrandTokens.spaceLg`). ZERO mudança de lógica. Padrão idêntico às outras telas empurradas (rede_screen como referência).
- [ ] Gates Flutter + commit: `feat(cliente): conexao com capa vibrante`.

### Task 3 (app): Speedtest na tela Conexão

**Files:** `apps/cliente-mobile/lib/features/conexao/speedtest_service.dart` (novo), `apps/cliente-mobile/lib/features/conexao/widgets/speedtest_card.dart` (novo), `apps/cliente-mobile/lib/features/conexao/conexao_screen.dart` (integração), `test/speedtest_service_test.dart` (novo)

- [ ] **Engine (`SpeedtestService`, sem dependência nova — usa o dio já presente):**
  - `Future<double> ping()` — 5 × HEAD `https://speed.cloudflare.com/__down?bytes=0`, mediana dos tempos em ms (descarta a 1ª, aquecimento de conexão).
  - `Future<double> download(void Function(double mbps) onProgress)` — GET `https://speed.cloudflare.com/__down?bytes=25000000` com `ResponseType.stream`, mede bytes/tempo com janelas de ~500ms chamando `onProgress` (velocímetro ao vivo), retorna média final em Mbps. Timeout 30s.
  - `Future<double> upload(void Function(double) onProgress)` — POST `https://speed.cloudflare.com/__up` com corpo de 10MB (bytes pseudo-aleatórios gerados em chunks), mesma medição. Timeout 30s.
  - Tudo cancelável (CancelToken) e com tratamento de erro → estado `falhou`.
  - Teste unitário da matemática (janelas → mbps) com clock/bytes injetáveis (a parte de rede não é testada — separar o cálculo puro numa função testável `mbpsFrom(bytes, duration)` e a mediana do ping).
- [ ] **UI (`SpeedtestCard`)** no topo da folha da tela Conexão: estado inicial com botão grande `Testar velocidade` (FilledButton primary); rodando: velocímetro semicircular (CustomPainter — arco de fundo + arco de progresso em `gradientPrimary`, valor central grande animado com a velocidade ao vivo, fase corrente "ping → download → upload" com ícones); resultado: 3 métricas lado a lado (↓ Mbps grande, ↑ Mbps, ping ms) + botão `Testar de novo` + nota discreta `Medido até a Cloudflare — resultado aproximado.` Estados de erro amigáveis. Dark mode ok (cores via tokens).
- [ ] Gates Flutter + commit: `feat(cliente): speedtest in-app na tela de conexao`.

### Task 4: Verificação da onda

- [ ] Gates Flutter completos + `flutter build apk --debug` + ruff nos arquivos da API.
- [ ] Review whole-branch (base = commit anterior à T1): régua intacta pro WhatsApp (diff aditivo!), idempotência, speedtest cancelamento/timeout/erros, tela conexão sem regressão.
- [ ] Checklist manual (Robert): rodar speedtest no aparelho (wifi e 4G), conferir push D-3/D0 após deploy (dá pra forçar mexendo numa fatura de teste no SGP), toggle da categoria faturas nas prefs.
