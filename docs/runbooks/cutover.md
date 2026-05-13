# Cutover runbook — Ondeline v2 (big-bang)

> Tag prereq: `m8-observabilidade-lgpd` shipped, CI verde, `m9-cutover` ready to tag at the end.

## TL;DR (operator-only)

Você (operador) executa este runbook. Cada bloco tem **timestamp** e **comandos exatos**.
Pause após cada bloco e confirme o output antes de avançar.

Em caso de qualquer falha: vá direto pra seção **Rollback** no fim deste arquivo.

---

## Pré-requisitos (checar uma vez, antes de qualquer outro passo)

```bash
# 1) Working tree limpo, tag m8 visível
git status
git tag | grep m8-observabilidade-lgpd

# 2) Hermes-3 gateway responde com o modelo certo
./scripts/check-hermes.sh

# 3) Variáveis sensíveis preenchidas no .env (não comitadas)
grep -E "^(JWT_SECRET|PII_ENCRYPTION_KEY|PII_HASH_PEPPER|EVOLUTION_HMAC_SECRET|EVOLUTION_KEY)=" .env | \
    awk -F= '{ if (length($2) < 16) print "EMPTY OR SHORT: " $1; else print "ok: " $1 }'

# 4) Postgres + Redis healthy
docker compose -f infra/docker-compose.dev.yml ps
```

Cada output deve estar verde. Se qualquer variável aparecer como `EMPTY OR SHORT`, **PARE** e
preencha primeiro.

---

## T-7d — Staging completo + E2E passing

Objetivo: rodar TUDO numa réplica isolada (subdomínio `*.staging.ondeline.<dominio>`) com
uma instância de Evolution apontada para essa réplica, e fazer 5 fluxos E2E à mão.

1. Subir staging (mesmas imagens prod, novo .env, novo Nginx Proxy host):
   ```bash
   # Copie .env para .env.staging com URLs/secrets de staging
   cp .env .env.staging
   # Edite: DATABASE_URL aponta para postgres-staging, REDIS_URL idem,
   # EVOLUTION_URL aponta para instância staging do Evolution.
   docker compose -f infra/docker-compose.prod.yml --env-file .env.staging \
       -p ondeline-staging up -d --build
   ```
2. Apply migrations + seed admin (no container staging):
   ```bash
   docker exec ondeline-staging-api alembic upgrade head
   ADMIN_EMAIL=admin@staging.test ADMIN_PASSWORD=$(openssl rand -base64 18) \
       ADMIN_NAME="Staging Admin" \
       docker exec -T -e ADMIN_EMAIL -e ADMIN_PASSWORD -e ADMIN_NAME \
       ondeline-staging-api python -m ondeline_api.scripts.seed_admin
   ```
3. Smoke remoto:
   ```bash
   API_BASE=https://api.staging.ondeline.<dominio> ./scripts/smoke-prod.sh
   ```
4. Os 5 fluxos E2E à mão (registre tempos em `T-7d-results.md` localmente):
   - **F1 — Cliente nova, suspenso por inadimplência:** WhatsApp do staging Evolution → bot pede CPF → identifica cliente suspenso → envia boletos. Esperado: 3 boletos máximo.
   - **F2 — Cliente ativo, problema técnico:** WhatsApp → bot pede CPF → cliente OK → fluxo de OS técnica → atendente humano vê na dashboard staging.
   - **F3 — Lead novo:** WhatsApp de número desconhecido → bot envia msg_boas_vindas → opção 2 → coleta nome → lead aparece na dashboard.
   - **F4 — Técnico PWA:** login no `tec.staging.ondeline.<dominio>` com user tecnico → vê OS atribuídas → iniciar (GPS) → concluir (CSAT + foto).
   - **F5 — LGPD export:** dashboard admin → cliente → export → ZIP baixa, contém cliente.json + conversas.json + ordens_servico.json.

Se algum dos 5 falhar, NÃO avance para T-3d. Investigue, corrija, e refaça F1-F5.

---

## T-3d — Smoke continuado em staging

Objetivo: rodar o smoke + observar `/healthz` e Grafana (se já provisionados) por
3 dias para pegar regressão silenciosa.

```bash
# Em uma sessão tmux/screen, deixar rodando a cada 5min
while true; do
    API_BASE=https://api.staging.ondeline.<dominio> ./scripts/smoke-prod.sh \
        || echo "$(date) — SMOKE FAILED" >> staging-smoke.log
    sleep 300
done
```

Se aparecer qualquer linha "SMOKE FAILED" durante 72h, investigue antes de continuar.

---

## T-1d — Backup do v1

Objetivo: garantir que existe um snapshot íntegro do v1 antes de cortar o tráfego.

```bash
./scripts/archive-v1.sh
# Output esperado:
#   Archive created: /root/BLABLA/ondeline-archive/v1-snapshot-YYYYMMDD.zip
#   Size: <N> bytes
#   SHA-256: <hash>
#   Items archived: bot.py dashboard.py config.json tecnicos.json conversas ordens_servico notificacoes bot.log dashboard.log

# Verificar conteúdo
unzip -l /root/BLABLA/ondeline-archive/v1-snapshot-*.zip | head -30

# Anotar o SHA-256 em algum lugar (não comitar)
```

Adicionalmente: snapshot do Postgres v2 também (estado pré-cutover):
```bash
./infra/pg_dump_local.sh
ls -la /root/BLABLA/ondeline-backups/
```

---

## T-0 — Cutover (window de ~15min de execução)

> **Antes de começar**: tenha 2 abas abertas
> - `docker compose -f infra/docker-compose.prod.yml logs -f api worker beat`
> - https://api.<dominio>/healthz refresh a cada 10s
>
> E o admin do Evolution num terceiro tab pronto pra apontar o webhook.

### (5min) Aviso WhatsApp aos clientes ativos
Use a UI antiga do dashboard v1 (ainda no ar) para disparar um broadcast manual aos
clientes em conversa ativa (estimar ~20-50 pessoas) com:

> "Olá! Vamos atualizar nosso atendimento agora e podemos ficar offline por ~10 minutos.
> Em instantes voltamos. Obrigado pela paciência! 😊"

Marque o horário do aviso. **Aguarde 5min** antes do passo seguinte.

### (1min) Stop v1
```bash
# Pegar PID
ps aux | grep -E 'bot\.py|dashboard\.py' | grep -v grep

# Parar bot e dashboard v1 (assumindo systemd ou nohup; ajuste se for outro mecanismo)
pkill -f 'python.*bot\.py' || true
pkill -f 'python.*dashboard\.py' || true

# Confirmar
ss -tlnp | grep -E '8700|8701' && echo "AINDA TEM PROCESSO V1 NA PORTA — INVESTIGAR" || echo "v1 desligado"
```

### (2min) Apontar webhook do Evolution para v2
No painel do Evolution (Evolution API admin UI) → instância `hermes-wa` → Settings → Webhook:

- **De**: `http://localhost:8700/webhook`
- **Para**: `http://api.ondeline:8000/webhook` (ou o nome do container/proxy correto que resolve da rede Evolution)

Salve. Anote o horário exato da troca.

### (5min) Smoke pós-cutover
```bash
API_BASE=https://api.<dominio> ./scripts/smoke-prod.sh
```
Output esperado: todas as linhas `OK`, último `SMOKE OK`.

Mande uma mensagem do **seu próprio WhatsApp** para o número Evolution:
> teste cutover

Esperado:
- `/healthz` mostra `celery.default` ou `celery.llm` incrementando momentaneamente
- Log do worker tem `inbound.process_inbound_message_task` + `evolution.send_outbound`
- Você recebe a resposta do bot v2

Se NÃO receber resposta em 30s → **Rollback** (próxima seção).

### Liga monitoramento + plantão por 2h
Mantenha:
- `docker logs -f ondeline-api ondeline-worker ondeline-beat` (filtro por `ERROR`/`WARNING`)
- `/healthz` aberto refreshing a cada 30s
- Grafana operational (se já provisionado) aberto na aba

Métricas alvo nas primeiras 2h:
- `ondeline_webhook_received_total` cresce (clientes mandando msg)
- `ondeline_evolution_send_total` cresce na mesma taxa
- `ondeline_evolution_send_failure_total` permanece em 0 ou ≤1% do total
- `ondeline_msgs_dedup_total` cresce um pouco (Evolution às vezes redelivera)
- `/healthz` checks db+redis sempre `ok`; celery queues nunca > 50 por mais de 1min

Sinais de alarme:
- Crescimento sustentado de filas (> 20 e crescendo): worker travado ou Hermes-3 fora
- 5xx no Nginx Proxy: aplicação caiu
- HMAC inválido alto (`ondeline_webhook_invalid_signature_total`): secret descasado entre Evolution e v2

---

## T+1d — Review

```bash
# Logs do dia
docker logs --since 24h ondeline-api 2>&1 | grep -iE 'error|exception' | head -50
docker logs --since 24h ondeline-worker 2>&1 | grep -iE 'error|exception' | head -50

# Métricas: snapshot do /metrics em algum lugar persistente
curl -s http://localhost:8000/metrics > "/root/BLABLA/ondeline-archive/metrics-cutover+1d-$(date +%Y%m%d).txt"

# Backups rodando?
ls -la /root/BLABLA/ondeline-backups/
```

Documente em um arquivo `T+1d-review.md` local:
- Total de mensagens processadas
- Total de OS criadas
- Lista de erros não-recorrentes (ignorar warnings transitórios)
- Itens para corrigir nos próximos dias

---

## T+7d — Limpeza do v1

Antes de remover o v1 do disco:

```bash
# Confirmar que o snapshot zip ainda está íntegro
sha256sum /root/BLABLA/ondeline-archive/v1-snapshot-*.zip

# Confirmar que 7 dias de tráfego passou pelo v2 sem incidente alto
docker logs --since 7d ondeline-api 2>&1 | grep -c ERROR
```

Se o número de ERROR está baixo (< 100, todos investigados), pode:
```bash
# Mover v1 (não deletar) — recupera espaço sem perda total
mv /root/BLABLA/ondeline-bot /root/BLABLA/ondeline-bot.retired-$(date +%Y%m%d)

# Reter o zip por 90d antes de apagar (recomendação)
echo "Keep zip until: $(date -d '+90 days' +%Y-%m-%d)" > /root/BLABLA/ondeline-archive/v1-snapshot.retention.txt
```

---

## Rollback

> Se você decidiu fazer rollback nas primeiras 24h, siga **estritamente** esta sequência.

### Critério de decisão
Rollback se:
- Bot v2 não responde a smoke (`scripts/smoke-prod.sh` falha por > 5min após cutover)
- Mais de 5 falhas Evolution consecutivas (`evolution_send_failure_total` cresce mais rápido que `evolution_send_total`)
- DB ou Redis fica inacessível por > 2min
- Você está confuso/cansado e prefere fazer rollback e tentar de novo amanhã

### Passos (~5min total)
1. **Apontar webhook Evolution de volta para v1**: admin Evolution → instância → webhook → `http://localhost:8700/webhook`. Salvar.
2. **Subir v1 de novo**:
   ```bash
   cd /root/BLABLA/ondeline-bot
   # Como o v1 estava sendo rodado antes — se foi via systemd/supervisord/nohup,
   # use o mesmo mecanismo. Exemplo nohup:
   nohup python3 bot.py > bot.log 2>&1 &
   nohup python3 dashboard.py > dashboard.log 2>&1 &
   # Confirma porta
   sleep 3 && ss -tlnp | grep 8700
   ```
3. **Smoke v1**:
   ```bash
   curl -s http://localhost:8700/healthz || curl -s http://localhost:8700/
   ```
4. **Aviso de retorno via WhatsApp** (broadcast manual via dashboard v1) → "Tudo certo, voltamos online! 😊"
5. **Pare a stack v2** (não derruba os dados — só os containers):
   ```bash
   docker compose -f infra/docker-compose.prod.yml down
   # ou em dev:
   docker compose -f infra/docker-compose.dev.yml down
   ```
6. **Post-mortem**: anotar em `cutover-rollback-YYYYMMDD.md` o que disparou o rollback, hipóteses, próximos passos. NÃO tentar refazer o cutover no mesmo dia.

---

## Nginx Proxy Manager (NPM) — config necessária

Antes do T-0, NPM precisa ter 3 proxy hosts apontando para os containers v2:

| Subdomínio | Forward to | Notes |
|---|---|---|
| `api.ondeline.<dominio>` | `ondeline-api:8000` HTTP | precisa `proxy_buffering off` no path `/api/v1/conversas/.*/stream` (SSE) |
| `admin.ondeline.<dominio>` | `<container do dashboard>:3000` HTTP | dashboard precisa apontar para `api.ondeline.<dominio>` via env |
| `tec.ondeline.<dominio>` | `<container do pwa>:3001` HTTP | mesmo |

**Custom config no NPM (Advanced tab do host `api.ondeline.<dominio>`)** — desabilitar buffering para SSE:
```nginx
location ~ ^/api/v1/conversas/.*/stream$ {
    proxy_pass http://ondeline-api:8000;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
    proxy_read_timeout 3600s;
}
```

Se você esquecer isso, o stream de chat na dashboard congela depois de poucos segundos
(o Nginx bufferiza eventos SSE). Fix one-line — mas precisa estar no lugar ANTES do cutover.
