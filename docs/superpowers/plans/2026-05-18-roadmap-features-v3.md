# Roadmap de Features — Maio/Junho 2026

Plano consolidado para 8 features novas, agrupadas em 4 fases por dependência e valor. Cada feature tem escopo, arquivos afetados, modelo de dados, riscos e critério de aceite.

> Convenção: **S** = ~1-2 dias, **M** = ~3-5 dias, **L** = ~1-2 semanas. Estimativas assumem 1 dev.

---

## Sumário

| # | Feature | Tamanho | Fase | Depende de |
|---|---|---|---|---|
| F0 | Nome do cliente em conversas (lista) | S | A | — |
| F1 | Resumo automático pra atendente humano | S | A | — |
| F2 | Régua de cobrança automática via WhatsApp | S | A | F3 (Pix QR) opcional |
| F3 | Pix dinâmico (QR Code BR Code) no boleto | M | A | — |
| F4 | Multi-instância WhatsApp (Comercial/Suporte) | M | B | — |
| F5 | A/B test de prompts/templates | M | B | F4 ajuda mas não bloqueia |
| F6 | Estoque do técnico (van) | M | C | — |
| F7 | Bot por voz (transcrição via Whisper) | L | D | — |

---

## Fase A — Quick wins (semana 1)

### F0 — Nome do cliente em lista de conversas

**Por quê.** Hoje `GET /api/v1/conversas` devolve `ConversaListItem` sem nome — só `whatsapp` + `cliente_id`. No detalhe (`ConversaOut`) o cliente vem embutido. A lista no dashboard mostra "5511…" em vez de "João Silva", o que dificulta o atendente identificar quem está esperando.

**Escopo.** Quando a conversa tem `cliente_id` (cliente já identificado via SGP), o item de lista mostra o nome.

**Arquivos.**
- `apps/api/src/ondeline_api/api/schemas/conversa.py` — adicionar `cliente_nome: str | None = None` em `ConversaListItem`.
- `apps/api/src/ondeline_api/repositories/conversa.py` — `list_paginated` faz `LEFT JOIN Cliente` e devolve nome descriptografado (Fernet via `decrypt_pii`).
- `apps/api/src/ondeline_api/api/v1/conversas.py` — popular `cliente_nome` na resposta.
- `apps/dashboard/components/conversa-list.tsx` — renderizar `cliente_nome ?? whatsapp_formatado`.
- `apps/api/tests/test_repo_conversa.py` — caso "lista com cliente identificado retorna nome".
- `apps/api/tests/test_api_conversas.py` (criar se faltar) — smoke do endpoint.

**Decisões.**
- Decifrar PII no backend (não no front) — front nunca lida com `nome_encrypted`.
- Truncar nome >24 chars no front com tooltip cheio (UX).
- Quando `cliente_id` é `None` (bot ainda não identificou), mostrar telefone formatado BR — reuso de `services/phone.format_br`.

**Riscos.**
- N+1 se o join não for feito no repo. Garantir `selectinload` ou JOIN explícito.
- Custo de decrypt em listagem grande: paginamos 50/página → 50 Fernet decrypts/req. Aceitável.

**Aceite.**
- [ ] Lista de conversas no dashboard mostra "João Silva" para conversas identificadas.
- [ ] Continua mostrando "(11) 9 8765-4321" pra conversas sem cliente.
- [ ] Sem N+1 (verificar com `SQLALCHEMY_ECHO=1` ou pytest-query-counter).

---

### F1 — Resumo automático pra atendente humano

**Por quê.** Quando bot escala (`transferir_para_humano` ou cliente pede humano), o atendente abre conversa e tem que ler 30-80 mensagens pra entender. TL;DR de 3 linhas reduz tempo médio de primeira resposta humana.

**Escopo.** Quando conversa entra em `ConversaEstado.HUMANO` (transição de bot → humano), enfileira job que chama o LLM com prompt "resuma em até 3 linhas: problema, o que o bot já tentou, próxima ação esperada". Resumo guardado em `Conversa.resumo_handoff` e mostrado no topo da tela de atendimento.

**Modelo.**
- Coluna nova em `conversas`: `resumo_handoff TEXT NULL`, `resumo_handoff_at TIMESTAMPTZ NULL`.
- Migração Alembic backward-compatible (ADD COLUMN NULL).

**Arquivos.**
- `apps/api/src/ondeline_api/db/models/business.py` — campos novos em `Conversa`.
- `apps/api/alembic/versions/<novo>_add_resumo_handoff.py` — migração.
- `apps/api/src/ondeline_api/services/conversa_events.py` ou novo `services/handoff_summary.py` — função `gerar_resumo_handoff(conversa_id)` que monta prompt, chama LLM, persiste.
- `apps/api/src/ondeline_api/workers/llm_turn.py` ou `workers/handoff.py` — task `gerar_resumo_handoff_task(conversa_id)` na fila `llm`.
- `apps/api/src/ondeline_api/services/inbound.py` — quando FSM emite ação de transferência humana, `enqueue_handoff_summary(conversa_id)`.
- `apps/api/src/ondeline_api/api/schemas/conversa.py` — `resumo_handoff` em `ConversaOut`.
- `apps/dashboard/components/conversa-detail.tsx` — card "Resumo" no topo se preenchido.
- Testes: `test_handoff_summary.py` (mocka LLM, valida persistência + idempotência).

**Decisões.**
- Idempotência: se `resumo_handoff_at` já existe e a conversa não recebeu novas mensagens humanas desde então, não regerar.
- Limite: `LLM_MAX_TOKENS` aplicado normalmente — resumo conta no budget diário da conversa.
- Privacidade: o resumo é texto livre derivado do conteúdo; tratar como PII (Fernet). Coluna `resumo_handoff_encrypted BYTEA` em vez de `TEXT`.

**Riscos.**
- LLM indisponível → atendente vê conversa sem resumo. Aceitável (graceful degrade).
- Resumo "alucinar" status → instruir prompt a só citar fatos das mensagens e nunca inferir contrato/pagamento.

**Aceite.**
- [ ] Ao transferir pra humano, em <10s aparece resumo no topo da conversa.
- [ ] Resumo é regenerado se cliente envia mais 5+ mensagens enquanto espera atendimento.
- [ ] Hermes offline não quebra escalação — só não mostra resumo.

---

### F2 — Régua de cobrança automática

**Por quê.** Maior alavanca de receita do roadmap. Faturas em aberto sem lembrete = inadimplência evitável.

**Escopo.** Beat job diário (ex: 09:00 BRT) varre clientes ativos com fatura em aberto e dispara mensagem nos gatilhos:

| Gatilho | Texto | Mídia |
|---|---|---|
| D-3 (3 dias antes do vencimento) | "Lembrete amigável: sua fatura vence em 3 dias" | boleto + Pix |
| D+1 | "Sua fatura venceu ontem" | boleto + Pix |
| D+5 | "5 dias de atraso — evite suspensão" | boleto + Pix |
| D+15 | "Aviso final antes da suspensão" | boleto + Pix |

Cliente pode desativar lembretes respondendo "PARAR" → opt-out persistido. Confirma com mensagem "Ok, não enviaremos mais lembretes de cobrança. Para receber boletos, peça a qualquer momento."

**Modelo.**
- Nova tabela `cobranca_lembrete`:
  ```
  id UUID PK
  cliente_id UUID FK NOT NULL
  fatura_id TEXT NOT NULL          -- id externo do SGP
  gatilho TEXT NOT NULL            -- 'D-3' | 'D+1' | 'D+5' | 'D+15'
  vencimento DATE NOT NULL
  enviado_em TIMESTAMPTZ NOT NULL
  UNIQUE(cliente_id, fatura_id, gatilho)
  ```
  → garante idempotência (não dispara duas vezes o mesmo gatilho na mesma fatura).
- Em `clientes`: `cobranca_optout BOOLEAN NOT NULL DEFAULT false`, `cobranca_optout_at TIMESTAMPTZ NULL`.

**Arquivos.**
- `apps/api/src/ondeline_api/db/models/business.py` — `CobrancaLembrete`, campos novos em `Cliente`.
- `apps/api/alembic/versions/<novo>_add_cobranca_lembrete.py`.
- `apps/api/src/ondeline_api/repositories/cobranca.py` — novo repo.
- `apps/api/src/ondeline_api/services/cobranca_regua.py` — orquestrador: itera clientes ativos, busca faturas via SGP (com cache), decide gatilhos pendentes, enfileira envio.
- `apps/api/src/ondeline_api/workers/cobranca_jobs.py` — task Celery `run_regua_cobranca()` (fila `notifications`).
- `apps/api/src/ondeline_api/workers/beat_schedule.py` — schedule cron diário 09:00 (Sao_Paulo).
- `apps/api/src/ondeline_api/services/inbound.py` — interceptar "PARAR" / "SAIR" antes do FSM quando vier de cliente conhecido em fluxo de cobrança. Persistir opt-out.
- `apps/api/src/ondeline_api/templates/cobranca/` — templates Jinja por gatilho.
- `apps/dashboard/app/(admin)/config/page.tsx` — toggle "Régua de cobrança ativa", config de horário.
- `apps/dashboard/app/(admin)/clientes/[id]/page.tsx` — flag "opt-out de cobrança" + histórico de lembretes enviados.

**Decisões.**
- **Horário fixo BRT** (não chamar 06h da manhã). Configurável via `Config` key `cobranca.horario` (default 09:00).
- **Quiet hours** absolutas: 21:00-07:00 — nunca enviar, mesmo se atrasou.
- **Janela de 24h do WhatsApp Business** não se aplica porque Evolution usa WA pessoal/comercial e não API oficial. Mas vale documentar limite.
- **Rate limit por número**: máx 1 mensagem de cobrança/dia/cliente (se cair 2 gatilhos no mesmo dia, manda só o mais grave).
- **Opt-out** zera no fechamento de nova fatura paga? **Não.** É permanente até cliente pedir pra reativar.
- **Suspensão real** continua sendo do SGP — esse sistema só avisa.

**Riscos.**
- **Spam → bloqueio do número WhatsApp**. Mitigar com quiet hours, opt-out claro, rate limit por número, e métrica `cobranca.opt_out_rate` — alerta se >10% optar em uma semana.
- **SGP fora do ar** → job tolera erro por cliente individual, não derruba batch inteiro. Retry com backoff.
- **Mudança de fatura** (cliente paga em D-1) → no D+1 a fatura sumiu da lista de abertas → job não dispara. ✅ idempotência via SGP.

**Aceite.**
- [ ] Beat dispara às 09:00 BRT.
- [ ] Cliente com fatura vencendo em 3 dias recebe exatamente 1 mensagem.
- [ ] Mesmo gatilho não dispara 2x na mesma fatura (constraint UNIQUE).
- [ ] "PARAR" desativa lembretes; "VOLTAR" reativa.
- [ ] Métrica `cobranca_lembrete_enviado_total{gatilho="D-3"}` em Prometheus.
- [ ] Dashboard mostra lembretes enviados nas últimas 24h.

---

### F3 — Pix dinâmico (QR Code BR Code) no boleto

**Por quê.** Hoje `enviar_boleto` manda o `codigo_pix` em texto **se** o SGP entregar (campo `codigoPix`). Falta: (a) confirmar quais faturas o SGP entrega o código (Ondeline vs LinkNetAM podem divergir), (b) gerar BR Code próprio quando o SGP não entregar, (c) enviar imagem QR Code junto.

**Pré-investigação (tarefa 0 da feature).**
- Auditar 1 semana de chamadas SGP em produção: quantas faturas vêm com `codigoPix` preenchido vs vazio.
- Verificar se Ondeline e LinkNetAM têm comportamento diferente (campo presente? formato BR Code v01 válido?).
- Decidir se vale fallback geral ou se >95% das faturas já vêm com Pix do SGP e o fallback é só pra exceção.

**Escopo.**
1. Renderizar QR Code PNG do `codigo_pix` quando o SGP entregar.
2. Quando SGP **não** entregar, gerar BR Code próprio (Pix estático com valor) usando chave Pix do provedor configurada no admin.
3. Sempre enviar: (a) PDF do boleto (atual), (b) imagem QR, (c) texto copia-e-cola.

**Arquivos.**
- `apps/api/pyproject.toml` — adicionar `qrcode[pil]` (~10kb runtime, sem dep nativa) + `crc` (ou implementar CRC16-CCITT inline) pra gerar BR Code.
- `apps/api/src/ondeline_api/services/pix_brcode.py` (novo) — `gerar_brcode(chave, nome, cidade, valor, txid) -> str` (formato EMV BR Code, validação CRC16).
- `apps/api/src/ondeline_api/services/pix_qr.py` (novo) — `gerar_qr_png(brcode: str) -> bytes` + cache Redis (TTL 1h).
- `apps/api/src/ondeline_api/tools/enviar_boleto.py` — fluxo:
  ```
  if fatura.codigo_pix:
      brcode = fatura.codigo_pix
  else:
      cfg = await config_repo.get_pix_config()
      if not cfg: log.warn + skip QR
      else: brcode = gerar_brcode(cfg.chave, cfg.nome, cfg.cidade, fatura.valor, fatura.id)
  png = gerar_qr_png(brcode)
  await evolution.send_media_bytes(jid, png, "image/png", caption="...")
  await evolution.send_text(jid, brcode)  # copia-e-cola
  ```
- `apps/api/src/ondeline_api/adapters/evolution.py` — `send_media_bytes(jid, bytes, mime, caption)` se não existir.
- Tabela `config` (já existe) — keys novas:
  - `pix.chave` (CPF/CNPJ/email/aleatória do provedor)
  - `pix.nome_beneficiario` (max 25 chars do BR Code)
  - `pix.cidade_beneficiario` (max 15 chars)
- `apps/dashboard/app/(admin)/config/page.tsx` — seção "Pix" com os 3 campos.
- `apps/api/tests/test_pix_brcode.py` — gerar BR Code, decodificar com lib externa (`pix-utils` em dev only) e validar.
- `apps/api/tests/test_pix_qr.py` — PNG válido + cache hit.

**Decisões.**
- **Prefere sempre o `codigo_pix` do SGP quando existir** (é dinâmico, com txid único). Fallback é Pix estático com valor.
- **Métrica** `pix_qr_source_total{fonte="sgp"|"gerado"|"indisponivel"}` mostra a saúde da fonte e ajuda a decidir se precisa pressionar SGP a sempre entregar.
- **Caption do QR**: "Aponte a câmera do app do seu banco aqui 👆".
- **Sem chave Pix configurada + SGP sem código** → log warning, envia só PDF + aviso "Pague pelo boleto anexo. Pix indisponível no momento."

**Riscos.**
- **BR Code mal-formado** → app do banco recusa. Mitigar com testes contra `pix-utils` (validador independente) + smoke test manual em pelo menos 3 bancos (Itaú, Nubank, BB).
- **Cliente paga Pix estático mas conciliação do SGP não bate** porque não tem txid — operacional, não técnico. Documentar no runbook.
- Imagem QR >5MB falha no WhatsApp — 256x256 PNG fica ~5kb, sem risco.

**Aceite.**
- [ ] Cliente recebe: (1) PDF do boleto, (2) imagem QR Pix, (3) texto Pix copia-e-cola — nessa ordem.
- [ ] QR funciona em Itaú, Nubank e BB (smoke manual).
- [ ] Faturas sem `codigo_pix` do SGP geram BR Code próprio com a chave configurada.
- [ ] Sem chave Pix configurada + SGP sem código → fluxo degrada (só PDF) sem quebrar.
- [ ] Métrica `pix_qr_source_total` mostra a divisão entre SGP/gerado.

---

## Fase B — Plataforma de canais e prompts (semana 2-3)

### F4 — Multi-instância WhatsApp

**Por quê.** Hoje há 1 instância Evolution (`hermes-wa`) atendendo tudo. Separar "Suporte" e "Comercial" permite:
- Prompts diferentes (comercial vende, suporte resolve).
- Filas de atendentes humanos distintas.
- Métricas por canal.
- Horários comerciais distintos.

**Escopo.** Refactor pra suportar N instâncias, cada uma com config independente (prompt, horário, fila de humanos, opt-out de cobrança ou não).

**Modelo.**
- Nova tabela `canal`:
  ```
  id UUID PK
  slug TEXT UNIQUE NOT NULL          -- 'suporte', 'comercial'
  nome TEXT NOT NULL                 -- exibição
  evolution_instance TEXT NOT NULL   -- nome da instância na Evolution API
  prompt_variant TEXT NOT NULL DEFAULT 'default'
  ativo BOOLEAN NOT NULL DEFAULT true
  horario_inicio TIME NULL
  horario_fim TIME NULL
  msg_fora_horario TEXT NULL
  created_at TIMESTAMPTZ NOT NULL
  ```
- Em `conversas`: `canal_id UUID FK NULL` (NULL = legado, default canal "suporte").
- Em `mensagens`: o canal é derivado da conversa.

**Arquivos.**
- `apps/api/src/ondeline_api/db/models/business.py` — `Canal`, FK em `Conversa`.
- `apps/api/alembic/versions/<novo>_add_canal.py` — cria tabela + popula 1 canal "suporte" + backfill `canal_id` em `conversas` existentes.
- `apps/api/src/ondeline_api/webhook/parser.py` — extrair `instance` do payload da Evolution (já vem no webhook).
- `apps/api/src/ondeline_api/services/inbound.py` — resolver `canal` por `instance` antes de criar/buscar conversa.
- `apps/api/src/ondeline_api/repositories/conversa.py` — `get_or_create_by_whatsapp_and_canal`.
- `apps/api/src/ondeline_api/adapters/evolution.py` — `EvolutionClient` parametrizado por instance (já é, mas hoje vem do settings — precisa virar runtime).
- `apps/api/src/ondeline_api/services/responder.py` — usar `canal.evolution_instance` ao enviar.
- `apps/api/src/ondeline_api/services/llm_loop.py` — passar `canal.prompt_variant` ao montar system prompt.
- `apps/api/src/ondeline_api/api/v1/canais.py` (novo) — CRUD admin.
- `apps/dashboard/app/(admin)/canais/page.tsx` (novo) — listar/editar canais.
- `apps/dashboard/components/conversa-list.tsx` — filtro por canal + badge na lista.
- Migração: backfill conversas existentes pro canal "suporte".

**Decisões.**
- **Mesmo cliente em 2 canais = 2 conversas distintas**. Cliente João pode falar no comercial e no suporte ao mesmo tempo, com históricos separados. Isso evita confusão de contexto pro LLM.
- ⚠️ **Marcado pra revisar quando essa fase chegar**: o usuário pediu pra deixar pendente como exatamente vamos modelar isso. Antes de implementar, decidir: (a) conversa única com tag de canal, (b) conversas separadas (atual), (c) outra abordagem. Re-discutir antes de gerar SPEC.
- **Webhook único** (`POST /webhook`) — discrimina canal pelo campo `instance` do payload Evolution. Não criamos endpoint por instância.
- **HMAC secret é por servidor Evolution**, não por instância — mantém um `EVOLUTION_HMAC_SECRET`.
- **Cada canal pode apontar pra Evolution diferente?** Não nessa fase. Mesma Evolution, múltiplas instâncias. (Multi-Evolution fica pra v4.)
- **Régua de cobrança (F2)** só dispara no canal "suporte" (definição: cliente esperado no suporte; comercial é prospect).

**Riscos.**
- **Migração quebra conversas em andamento** → fazer backfill ANTES de marcar `canal_id NOT NULL`. Coluna nasce nullable + backfill + deploy + segunda migração (semana seguinte) marca NOT NULL.
- **Prompt errado no canal errado** → testar `prompt_variant` resolve corretamente em CI.
- **Confusão operacional**: atendente atendendo no canal errado. Mitigar com badge visual claro.

**Aceite.**
- [ ] 2 instâncias Evolution registradas, ambas recebem mensagens.
- [ ] Conversa do canal "comercial" usa prompt comercial; "suporte" usa prompt suporte.
- [ ] Dashboard filtra por canal.
- [ ] Cliente atendido em 2 canais tem 2 conversas independentes.
- [ ] Migração roda sem perda de mensagens existentes.

---

### F5 — A/B test de prompts/templates

**Por quê.** Mudanças no prompt são jogadas no escuro hoje. Comparar variantes em paralelo permite decidir por dado, não por achismo.

**Escopo.** Sistema de variantes nomeadas. Cada conversa é atribuída deterministicamente a uma variante (hash do `whatsapp` % buckets). Dashboard mostra métricas por variante: taxa de resolução sem humano, satisfação (CSAT), turnos médios, tokens médios.

**Modelo.**
- Aproveita `LlmEvalSample` já existente (anotar `prompt_variant`).
- Nova tabela `prompt_variant`:
  ```
  id UUID PK
  nome TEXT UNIQUE NOT NULL          -- 'default', 'v2-warmer', 'v2-direct'
  system_prompt TEXT NOT NULL
  ativo BOOLEAN NOT NULL DEFAULT true
  trafego_pct INT NOT NULL DEFAULT 0  -- 0-100, soma das ativas <= 100
  canal_slug TEXT NULL                -- restrição opcional por canal (F4)
  created_at TIMESTAMPTZ NOT NULL
  created_by UUID FK users(id)
  ```
- Em `conversas`: `prompt_variant TEXT NULL` (preenchido na 1ª chamada LLM, imutável depois).

**Arquivos.**
- `apps/api/src/ondeline_api/db/models/business.py` — `PromptVariant`, campo em `Conversa`.
- `apps/api/alembic/versions/<novo>_add_prompt_variant.py`.
- `apps/api/src/ondeline_api/services/prompt_router.py` (novo) — `escolher_variante(whatsapp, canal) -> PromptVariant`. Bucketing: `int(sha256(whatsapp)[:8], 16) % 100`.
- `apps/api/src/ondeline_api/services/llm_loop.py` — usa variante da conversa (ou escolhe na primeira chamada).
- `apps/api/src/ondeline_api/repositories/eval.py` — agregação por `prompt_variant`.
- `apps/api/src/ondeline_api/api/v1/prompts.py` (novo) — CRUD admin.
- `apps/api/src/ondeline_api/api/v1/metricas.py` — endpoint `/api/v1/metricas/prompts/comparar` retorna métricas por variante.
- `apps/dashboard/app/(admin)/prompts/page.tsx` (novo) — editor de variantes + tráfego.
- `apps/dashboard/app/(admin)/metricas/prompts/page.tsx` (novo) — comparação A/B.

**Métricas comparadas.**
- Taxa de escalação humana (lower = better).
- Turnos médios até resolução.
- CSAT médio (já planejado em F8 do roadmap geral; aqui só fica esperando).
- Tokens médios/conversa (custo).
- Tempo de resolução.

**Decisões.**
- **Bucketing por `whatsapp`** garante que mesmo cliente sempre cai na mesma variante (não confunde experiência ao longo de N conversas).
- **Imutável após primeira atribuição** → resultados não contaminam.
- **Soma de tráfego ≤ 100%**. O restante (se <100) cai em `default`. Validar em CRUD.
- **Sem ML automático** nessa fase — admin decide quando promover variante a 100%.

**Riscos.**
- **Variante ruim em produção** → toggle "desativar" zera tráfego dela. Conversas em curso terminam com a variante.
- **Sample size pequeno** → mostrar intervalo de confiança / aviso "amostra insuficiente" quando n<50.

**Aceite.**
- [ ] Admin cria variante "v2-direct" com 20% de tráfego.
- [ ] 20% das conversas novas usam o novo prompt; 80% seguem default.
- [ ] Após 1 semana, dashboard mostra comparação lado-a-lado.
- [ ] Desativar variante zera tráfego sem quebrar conversas em andamento.

---

## Fase C — Operação de campo (semana 3-4)

### F6 — Estoque do técnico (van)

**Por quê.** Equipamentos (ONU, roteador, cabos, conectores) saem do almoxarifado pra van do técnico e se perdem. Sem rastreio. Em ISP pequeno isso é prejuízo direto e mensurável.

**Escopo.**
- **Catálogo** de itens (modelos de ONU/roteador, com SKU).
- **Saldo** por técnico (van).
- **Movimentações**: entrada (almoxarifado → van), saída (van → cliente, baixa na conclusão de OS), devolução (van → almoxarifado), perda.
- **Auditoria** mensal (técnico faz inventário pelo PWA, sistema mostra divergência).

**Modelo.**
```
item:
  id UUID PK
  sku TEXT UNIQUE NOT NULL
  nome TEXT NOT NULL
  categoria TEXT NOT NULL   -- 'onu', 'roteador', 'cabo', 'conector', 'outro'
  serializado BOOLEAN NOT NULL DEFAULT false  -- ONU tem serial, conector não
  ativo BOOLEAN NOT NULL DEFAULT true

estoque_movimento:
  id UUID PK
  item_id UUID FK NOT NULL
  tecnico_id UUID FK NULL              -- NULL = almoxarifado
  tipo TEXT NOT NULL                   -- 'entrada' | 'saida' | 'devolucao' | 'perda' | 'ajuste'
  quantidade INT NOT NULL              -- positivo
  serial TEXT NULL                     -- se item.serializado
  ordem_servico_id UUID FK NULL        -- baixa amarrada a uma OS
  origem_tecnico_id UUID FK NULL       -- pra transferência van→van
  observacao TEXT NULL
  criado_por UUID FK users(id) NOT NULL
  criado_em TIMESTAMPTZ NOT NULL
  INDEX (tecnico_id, item_id)
  INDEX (ordem_servico_id)

estoque_saldo (view materializada ou tabela com trigger):
  tecnico_id UUID
  item_id UUID
  saldo INT
  PK (tecnico_id, item_id)
```

**Arquivos.**
- `apps/api/src/ondeline_api/db/models/estoque.py` (novo).
- `apps/api/alembic/versions/<novo>_add_estoque.py` — tabelas + view materializada (refresh por trigger ou recompute on read).
- `apps/api/src/ondeline_api/repositories/estoque.py` — CRUD + saldo.
- `apps/api/src/ondeline_api/services/estoque.py` — regras (saldo não pode ficar negativo; baixa em OS exige saldo).
- `apps/api/src/ondeline_api/api/v1/estoque.py` — endpoints admin e PWA:
  - `GET /api/v1/estoque/itens` — catálogo.
  - `GET /api/v1/estoque/saldo?tecnico_id=` — saldo (admin: qualquer; técnico: só o próprio).
  - `POST /api/v1/estoque/movimento` — registrar entrada/saída/devolução.
  - `POST /api/v1/estoque/inventario` — auditoria mensal.
- `apps/dashboard/app/(admin)/estoque/` — catálogo de itens, saldo por técnico, movimentações, relatório de divergência.
- `apps/tecnico-pwa/app/(tec)/estoque/page.tsx` — saldo da minha van + histórico.
- `apps/tecnico-pwa/app/(tec)/os/[id]/concluir.tsx` — passo "qual equipamento entregou?" → cria movimento de saída atrelado à OS.
- Migração precisa popular catálogo inicial (3-5 SKUs comuns).

**Decisões.**
- **Serial obrigatório em ONU/roteador**. Conector/cabo é por quantidade.
- **Baixa só na conclusão da OS**, não na atribuição. Técnico pode estar entre 2 OS com a mesma ONU e a gente não sabe qual instalou primeiro.
- **Saldo negativo bloqueia**. Se técnico tenta baixar item sem saldo, erro explicativo. Mas admin pode forçar (movimento `ajuste` positivo).
- **Sem multi-almoxarifado** nessa fase (1 almoxarifado central + N técnicos).

**Riscos.**
- **Resistência dos técnicos** a registrar — UI tem que ser 1-tap. Pré-seleciona modelo padrão. Scan de código de barras (Web Barcode Detection API no PWA, já suportado em Chrome Android) acelera.
- **Saldo dessincronizado** se houver bug → endpoint "recomputar saldo" idempotente que conta movimentos do zero.

**Aceite.**
- [ ] Admin cadastra 3 SKUs de ONU e dá entrada de 10 unidades de cada na van do João.
- [ ] João abre PWA, vê "ONU XPON ZTE: 10".
- [ ] João conclui OS e seleciona "ONU XPON ZTE — serial X123" → saldo cai pra 9, movimento atrelado à OS.
- [ ] Admin abre relatório e vê: 1 OS, 1 ONU baixada, serial X123.
- [ ] Inventário mensal: técnico digita "tenho 9 ONUs" — sistema confirma, sem divergência.

---

## Fase D — Voz (semana 4-5)

### F7 — Bot por voz (transcrição via OpenAI Whisper API)

**Por quê.** Brasileiro manda áudio. Hoje o `media_classifier` devolve "ack" ou escala humano. Transcrever automaticamente expande cobertura do bot pra 100% das mensagens.

**Decisão arquitetural.** Usar **OpenAI Whisper API** (`api.openai.com/v1/audio/transcriptions`) em vez de container local. Justificativa:
- Latência ~1-2s (vs 3-5s local em CPU).
- Sem dor de operação (modelo, RAM, GPU, cold start).
- Custo previsível: ~US$ 0.006/min. 1000 áudios/dia × 15s médio = 250min = ~US$ 1.50/dia = ~US$ 45/mês.
- Trade-off: áudio sai da infra — **mitigar com aviso explícito ao cliente** e documentar no aviso de privacidade.

**Escopo.** Quando inbound é áudio (`InboundKind.AUDIO`):
1. Baixa áudio temporário da Evolution.
2. POST multipart pra OpenAI `/v1/audio/transcriptions` (`model=whisper-1`, `language=pt`).
3. Recebe transcrição.
4. Trata como mensagem de texto normal (mesmo fluxo FSM + LLM).
5. Persiste áudio (URL) + transcrição (Fernet-encrypted).

**Modelo.**
- Em `mensagens`: adicionar `transcricao_encrypted BYTEA NULL`, `transcricao_status TEXT NULL` (`pending|ok|failed|skipped`).

**Arquivos.**
- `apps/api/pyproject.toml` — já tem `httpx`, então só código novo. Sem dep nativa.
- `apps/api/src/ondeline_api/config.py` — `openai_api_key`, `openai_asr_model="whisper-1"`, `openai_asr_max_seconds=120`.
- `apps/api/src/ondeline_api/adapters/asr/openai_whisper.py` (novo) — cliente:
  - Download do áudio da URL (httpx async).
  - Recusa se >25MB (limite OpenAI) ou se duração estimada > `openai_asr_max_seconds`.
  - POST multipart pra OpenAI com timeout 30s.
  - Retry idempotente: 1 retry em 5xx ou timeout.
- `apps/api/src/ondeline_api/services/asr.py` (novo) — orquestrador: download → chama adapter → persiste transcrição → re-injeta no pipeline inbound.
- `apps/api/src/ondeline_api/workers/asr_jobs.py` (novo) — task `transcrever_audio(mensagem_id)` em fila nova `asr` (ou reaproveita `llm` se preferir economizar fila).
- `apps/api/src/ondeline_api/workers/queues.py` + `beat_schedule.py` — registrar fila `asr` se for nova.
- `infra/docker-compose.prod.yml` — adicionar `asr` à lista de filas do worker: `-Q default,llm,sgp,notifications,asr`.
- `apps/api/src/ondeline_api/services/inbound.py` — quando `InboundKind.AUDIO`:
  - Salva mensagem com `transcricao_status='pending'`.
  - Envia ACK imediato pro cliente: "🎧 Recebi seu áudio, vou ouvir e já respondo".
  - Enfileira `transcrever_audio(mensagem_id)`.
  - **Não roda FSM nessa entrada** — quem reentra no FSM é o callback do worker ASR depois de transcrever.
- `apps/api/alembic/versions/<novo>_add_transcricao.py`.
- `apps/dashboard/components/conversa-detail.tsx` — exibir transcrição abaixo do player de áudio + badge "🤖 transcrito".
- `infra/.env.example` — `OPENAI_API_KEY=` + `OPENAI_ASR_MODEL=whisper-1` + `OPENAI_ASR_MAX_SECONDS=120`.
- Testes: `test_asr.py` (mocka httpx, valida fluxo + retry + skip por tamanho).

**Decisões.**
- **OpenAI Whisper API** — confirmado pelo usuário. Sem Whisper local.
- **`language=pt`** no request — reduz erro e tempo.
- **Áudios >2min são `skipped`** com resposta "Áudio longo — pode me resumir por texto?".
- **Falha de transcrição** → resposta "Não consegui ouvir o áudio. Pode me mandar por texto?".
- **Custo controlado**: contador diário em Redis `asr:tokens:YYYY-MM-DD` (na verdade segundos transcritos). Alerta Prometheus se ultrapassar threshold/dia.
- **LGPD / privacidade**:
  - Avisar no primeiro áudio recebido por cliente: "_Usamos transcrição automática para te atender mais rápido. Seu áudio é processado pela OpenAI e descartado. Se preferir, escreva por texto._" — guardar flag `cliente.asr_aviso_enviado_at` pra não repetir.
  - OpenAI não treina com dados de API por padrão desde 2023, mas vale citar no aviso interno.
  - Atualizar política de privacidade / runbook LGPD.
- **Fila separada `asr`** — evita travar `llm` em pico de áudios. Configurar worker com concurrency=2 nessa fila (não precisa muito).

**Riscos.**
- **OpenAI fora do ar / chave inválida** → `transcricao_status='failed'`, bot responde pedindo texto. Métrica `asr_failure_total`.
- **Áudio com ruído / sotaque pesado** → transcrição ruim → LLM responde mal. Mitigar com confidence score se a API expuser (Whisper API não expõe score por enquanto — limitação aceita).
- **Custo explode** se bot for spam-bombed → rate limit por número (mesmo do F2) + circuit breaker se gasto/dia > N.
- **PII em áudio** vai pra OpenAI — risco regulatório. Mitigado com aviso explícito e desabilitação de treino.

**Aceite.**
- [ ] Cliente manda áudio "tô sem internet" → bot responde igual ao texto equivalente.
- [ ] Mensagem no banco tem áudio + transcrição.
- [ ] Latência média ponta-a-ponta < 8s.
- [ ] Áudio >2min → resposta pedindo texto, sem custo OpenAI.
- [ ] OpenAI fora do ar → resposta gracefulle pedindo texto.
- [ ] Dashboard mostra transcrição abaixo do player.
- [ ] Primeiro áudio do cliente gera aviso de privacidade; subsequentes não repetem.
- [ ] Métrica `asr_seconds_total` em Prometheus alimenta painel de custo.

---

## Sequenciamento e dependências

```
Semana 1   Semana 2   Semana 3   Semana 4   Semana 5
─────────  ─────────  ─────────  ─────────  ─────────
F0 F1 F2   F4         F4 (cont)  F6 (cont)  F7 (cont)
F3         F5         F6         F7
```

- **Paralelizável dentro da fase A** (F0/F1/F2/F3 são independentes).
- **F4 antes de F5** se possível (variante por canal fica mais limpa) — mas F5 funciona com 1 canal só.
- **F6 e F7 podem ir em paralelo** se houver capacidade — não tocam o mesmo código.

---

## Itens transversais (aplicar em todas)

1. **Migrações backward-compatible**: toda coluna nova nasce `NULL` ou com default; constraints `NOT NULL` chegam em migração subsequente após backfill.
2. **Testes mínimos por feature**: 1 happy path + 1 borda + 1 falha de dependência externa (LLM/SGP/Whisper indisponível).
3. **Métricas Prometheus** novas: `cobranca_lembrete_enviado_total`, `handoff_summary_generated_total`, `pix_qr_generated_total`, `asr_duration_seconds`, `prompt_variant_in_use{variant=…}`, `estoque_movimento_total{tipo=…}`.
4. **Feature flags** via tabela `Config` (já existe): cada feature começa atrás de flag `feature.cobranca_regua.enabled` etc. Permite rollback sem deploy.
5. **Logs PII-masked**: telefone, CPF, transcrição, resumo — todos mascarados nos structlog (`services/pii_mask.py`).
6. **Documentação**: cada feature ganha runbook em `docs/runbooks/` (como ligar/desligar, métricas, troubleshooting).

---

## Próximos passos

1. Revisar este plano e priorizar/cortar features se necessário.
2. Para cada feature aprovada, gerar SPEC detalhada (`/gsd:spec-phase`) com falsifiable requirements.
3. Depois SPEC → PLAN executável (`/gsd:plan-phase`) com tarefas atômicas.
4. Executar fase-a-fase, mergeando incrementalmente.
