# Plano de Evolução — Ondeline

Estudo de viabilidade e plano em fases pra evolução do sistema, baseado em
análise do código atual (não em chute). Cada item tem **o que existe hoje**,
**o que falta**, **esforço real** e **risco**.

> Última atualização: 2026-05-28.

---

## Quadro geral — 9 frentes priorizadas

```
Fase 1 (Auth)  ───┐
                  ├──► Fase 3 (Engajamento) ───┐
Fase 2 (Obs)   ───┘                            ├──► Fase 4 (Loyalty)
[Publicar lojas em paralelo] ──────────────────┘
```

Total estimado: **~4 semanas** de dev, com a publicação nas lojas rodando em
paralelo.

---

## Fase 1 — Auth seguro (3-5 dias)

### 1.1 Refresh token (tecnico-mobile, depois cliente-mobile)

**Hoje:**
- Backend já tem `encode_refresh_token` em `jwt.py:76` (TTL 7d, payload com `jti` + comentário "token_hash em DB").
- Settings já tem `refresh_token_ttl_days: int = 7`.
- Cliente Flutter (`tecnico-mobile/lib/core/api/api_client.dart:37`) tem TODO no interceptor 401.
- Não existe rota `/auth/refresh` exposta.
- Não existe tabela `refresh_token_revoked` (ou similar).

**Falta:**
1. Migration: tabela `refresh_token` (`jti UUID PK`, `user_id FK`, `token_hash`, `expires_at`, `revoked_at?`, `created_at`).
2. Rota `POST /auth/refresh` recebendo refresh token via **cookie httpOnly**, validando `jti` ativo no DB, emitindo novo access (e rotacionando refresh).
3. Rota `POST /auth/logout` invalidando o `jti` (revogação).
4. Mexer no login (`/auth/login`): além de access, set-cookie do refresh.
5. **No tecnico-mobile**: interceptor 401 → tenta `/auth/refresh` → se OK, refaz a request original; se falhar, limpa sessão (comportamento atual).
6. **No cliente-mobile**: replicar mesma lógica.

**Esforço:** 1-2 dias.
**Risco:** baixo (padrão bem documentado).

### 1.2 Rate limit por CPF (slowapi key_func custom)

**Hoje:**
- `slowapi` configurado em `api/webhook.py:31` com `key_func=get_remote_address`.
- `cliente_app_auth.py` usa esse `limiter` com `_RL_OTP = "60/hour"` e `_RL_AUTH = "120/hour"`.
- Atrás do nginx, todo request vem do mesmo IP (bridge Docker) → limite vira **global**.

**Falta:**
1. `key_func` customizada que extrai CPF do body da request (`request.json()` é assíncrono; usar `await request.body()` e parse manual ou middleware que injeta no `request.state.cpf`).
2. Aplicar só em `/auth/*` (manter IP em outras rotas como webhook).
3. Sobrescrever limit com decorator próprio que usa a key custom.

**Esforço:** 2-4h.
**Risco:** baixo. Cuidado com endpoints sem CPF (fallback pra IP).

---

## Fase 2 — Observabilidade (3-5 dias)

> 🎯 **Escopo decidido (2026-05-28):** fazer SOMENTE **2.2** (métricas WhatsApp
> templates) e **2.3** (métricas OTP Cloud vs Evolution). A **2.1** (OpenTelemetry
> + Tempo) fica adiada — pode entrar depois da Fase 4 ou ser repriorizada.

### 2.1 OpenTelemetry → Grafana Tempo *(ADIADO)*

**Hoje:** **tudo já instalado e instrumentado** (FastAPI, Celery, httpx, SQLAlchemy, Redis). `services/otel_init.py` chamado no startup da API e do worker. `config.otel_exporter_otlp_endpoint` vazio = OTel desligado.

**Falta:**
1. Adicionar serviço `tempo` em `infra/docker-compose.prod.yml` (Grafana Tempo).
2. Setar `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318` no `.env`.
3. Dashboards Grafana básicos (já tem Grafana? se não, subir junto).
4. Configurar retenção (storage local cresce; 7-14 dias é razoável).

**Esforço:** 3-4h.
**Risco:** médio — cuidar de storage.

### 2.2 Métricas WhatsApp templates

**Hoje:** parser do webhook Cloud (`webhook/parser_cloud.py:52`) **já captura** status updates (sent/delivered/read/failed). O handler em `api/webhook_cloud.py:106` só loga (`webhook_cloud.message_status`).

**Falta:**
1. Migration: tabela `whatsapp_message_status` (`wamid`, `template_name`, `status`, `timestamp`, `error?`).
2. Persistência no webhook handler.
3. Endpoint admin `/api/v1/admin/whatsapp-metricas`: agregação por template (entregue/lido/falha + taxas).
4. Widget no dashboard: tabela com taxa de entrega/leitura/clique por template + sparkline 7d.

**Esforço:** 1-2 dias.
**Risco:** médio (volume; usar partição por mês se crescer).

### 2.3 Métricas OTP Cloud vs Evolution

**Hoje:** logs estruturados (`otp.primary_send_failed_fallback`, `otp.cloud_canal_not_found`) já saem do `cliente_app_otp.issue()`.

**Falta:**
1. `prometheus_client` (se não tem) + Counter `otp_send_total{provider,result}`.
2. Incrementar contador no `issue()` (success/fallback/error).
3. Widget no dashboard com split Cloud vs Evolution + taxa de fallback.

**Esforço:** 4-6h.
**Risco:** baixo.

---

## Fase 3 — Engajamento (5-7 dias)

### 3.1 App Links cliente-mobile

**Hoje:** padrão já validado no tecnico-mobile (commit que abre OS direto no app). cliente-mobile tem deep link custom `clientemobile://` mas Meta só aceita https.

**Falta:**
1. Decidir host (`app.ondeline.com.br`? `cli.robertbr.dev` temporário?).
2. Replicar pra cliente-mobile: `intent-filter` no manifest + `Runner.entitlements` (capability Xcode) + `/.well-known/assetlinks.json` + `apple-app-site-association`.
3. Rotas a deeplinkar: `/faturas`, `/faturas/:id`, `/os/:id`, `/notificacoes`.
4. Atualizar templates WhatsApp pra usar essas URLs nos botões "Ver no app".

**Esforço:** 4-6h.
**Risco:** baixo.
**Dependência:** **cliente-mobile publicado nas duas lojas** pra Universal Links iOS funcionar 100%.

### 3.2 Segmentos de promoções (inadimplentes / adimplentes)

**Hoje:** backend já tem coluna `segmento` em `Promocao` com docstring listando os 4 valores (`todos`, `inadimplentes`, `adimplentes`, `plano:<id>`). Função `_match_segmento` em `cliente_app_promocoes.py:78` só trata `"todos"`.

**Falta:**
1. Query SGP/cache pra status financeiro do user (atraso > 0 = inadimplente).
2. Função `_match_segmento` real (cobrir os 4 casos).
3. Habilitar opções no dropdown do `promocao-form-dialog.tsx` (tirar o "(TODO)").

**Esforço:** 1 dia.
**Risco:** médio (SGP tem rate limit; usar `sgp_cache_ttl_cliente: int = 3600`).

### 3.3 Notas Play vinculadas ao changelog

**Hoje:** sem automação. Notas da versão são preenchidas à mão na Play Console.

**Falta:**
1. Convenção de commits (`feat:`, `fix:`, `chore:` — já estamos usando).
2. GitHub Action `release.yml` que ao criar tag `v1.0.x`:
   - Gera CHANGELOG.md (via `git-cliff` ou similar).
   - Faz upload do CHANGELOG como release notes via Google Play API (precisa de service account JSON).
3. (Opcional) Mesmo pra App Store via App Store Connect API.

**Esforço:** 4-6h.
**Risco:** baixo.

---

## Fase 4 — Loyalty progressivo (Diamante) (7-10 dias)

**Hoje:** fidelidade básica com **pontos por missão** e **resgate** (`ClienteAppFidelidadeResgate`). Sem tier nem antiguidade.

**Falta:**

**4.1 Discovery (1-2 dias)** — decisões de produto:
- Quais tiers? Bronze / Prata / Ouro / Diamante?
- Régua: tempo de casa + pontos acumulados (qual o peso de cada)?
- Quais benefícios reais por tier? (desconto na fatura, prioridade no suporte, brindes, gift na conta de aniversário?)
- Cliente pode "descer" de tier ou só sobe?

**4.2 Implementação (5-7 dias):**
1. Migration: campo `tier` em `cliente_app_user` (enum) + tabela `tier_historico` (transições).
2. Cálculo automático (cron diário no Celery, lê SGP pra tempo de casa).
3. Widget no app cliente: card "Seu nível" + barra de progresso pro próximo + benefícios desbloqueados.
4. Tela no admin: relatório de clientes por tier + transições.
5. Missão nova: "Alcançar próximo tier".
6. (Opcional) Push template "Você subiu de nível!" — precisa de auth template novo no Meta.

**Esforço:** ~1 sprint (7-10 dias).
**Risco:** **alto risco de produto** — régua errada frustra cliente sem aumentar retenção. Discovery bem-feita é essencial.
**Dependência:** Fase 2 (pra calibrar com dados reais).

---

## Hosts atuais

| App | Host atual | Host alvo (futuro) |
|-----|-----------|--------------------|
| tecnico-pwa | `https://tec.robertbr.dev` | `https://tecnico.ondeline.com.br` (planejado) |
| cliente-pwa (se existir / TODO) | — | `https://app.ondeline.com.br` (sugestão) |
| API | `https://apiblabla.robertbr.dev` | mesmo? |

Quando migrar de host, ver checklist no `docs/whatsapp-cloud-templates.md`.
