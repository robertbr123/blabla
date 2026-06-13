# Comunicados / Disparo em Massa via WhatsApp Cloud API — Design

**Data:** 2026-06-13
**Status:** Aprovado (aguardando review do spec)
**Abordagem de envio:** C (híbrido) — modelo de campanha próprio + reaproveitamento do miolo de envio do `notify_sender`.

## Contexto e problema

O provedor já tem o canal oficial da Meta (WhatsApp Cloud API) integrado, mas **não existe** uma forma de disparar mensagens em massa (comunicados, links, promoções) para a base de clientes. Caso motivador: lançamento do app — disparar para muitos clientes um texto com o link de download. Precisa ser **segmentável** (cidade, status, plano, ou base inteira) e permitir **exportar** o recorte de clientes (telefone, cidade e outros campos úteis a um provedor).

## Restrição central: regra das 24h / template obrigatório

No canal oficial da Meta, **não se pode** enviar texto livre para quem não mandou mensagem nas últimas 24h. Para disparo em massa é **obrigatório** usar um **template pré-aprovado** pela Meta (categoria Marketing ou Utility). O texto não é digitado livremente no disparo — está num template aprovado; o que se preenche na hora são as **variáveis** dele (ex: `{{1}}` = link do app).

Consequência: o adapter de envio precisa ser Cloud (`provider=cloud`). O Evolution **não** suporta template e fica de fora desta feature.

## Infraestrutura existente reaproveitada

- `CloudAdapter.send_template(jid, name, language, body_params, header_media_url, otp_code)` — `apps/api/src/ondeline_api/adapters/whatsapp/cloud.py`
- `Canal` (provider cloud/evolution) — `apps/api/src/ondeline_api/db/models/business.py`
- `Cliente` com `whatsapp`, `cidade`, `plano`, `status`, `deleted_at`, `cobranca_optout` (indexados) — mesmo arquivo
- `WhatsAppMessageStatus` (wamid, sent/delivered/read/failed) + webhook de status — `services/whatsapp_message_log.py`
- Pipeline de envio `notify_sender` (resolução de adapter por canal, envio, log) — `workers/notify_sender.py`
- Fila Celery `notifications` — `workers/celery_app.py`

## Decisões aprovadas

1. **Templates: misto.** Começa com 2-3 templates reutilizáveis; porta aberta para submeter novos no futuro.
2. **Segmentação:** cidade + status + plano combináveis, ou nenhum filtro = base inteira. Sempre respeita opt-out.
3. **Export ligado ao filtro:** o mesmo recorte que dispara também baixa em CSV/Excel.
4. **Agendamento:** campo `agendada_para` existe no modelo, mas MVP entrega só "enviar agora". Agendar = extensão futura.
5. **Opt-out de marketing:** coluna nova `marketing_optout`, sempre respeitada. Auto-opt-out por resposta "SAIR"/"PARAR" = extensão futura (anotada).

---

## 1. Modelo de dados

### Tabela `campanhas`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `titulo` | str | nome interno da campanha |
| `canal_id` | FK → `canais` | obrigatório `provider=cloud` (validado) |
| `template_name` | str | nome do template aprovado na Meta |
| `template_language` | str | ex: `pt_BR` |
| `body_params` | JSONB | valores das variáveis, ex: `{"1": "https://apps.apple.com/..."}` |
| `header_media_url` | str \| null | para template com header de imagem |
| `segmentacao` | JSONB | `{cidade?, status?, plano?}`; vazio = base inteira |
| `status` | str | `rascunho \| enviando \| concluida \| cancelada \| erro` |
| `total_destinatarios` | int | preenchido no disparo |
| `enviadas` | int | contador |
| `falhas` | int | contador |
| `agendada_para` | datetime \| null | reservado p/ extensão de agendamento |
| `created_by` | FK → user | quem criou |
| `created_at` / `started_at` / `finished_at` | datetime | |

### Tabela `campanha_destinatarios`
Uma linha por cliente do disparo. Fonte de verdade do progresso + garante idempotência.
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `campanha_id` | FK → `campanhas` | |
| `cliente_id` | FK → `clientes` | |
| `whatsapp` | str | snapshot no momento do disparo |
| `status` | str | `pendente \| enviada \| entregue \| lida \| falha` |
| `wamid` | str \| null | id da mensagem na Meta |
| `erro` | str \| null | motivo da falha |
| `enviada_em` | datetime \| null | |

Índice em (`campanha_id`, `status`) para progresso; índice em `wamid` para o webhook localizar.

### Tabela `broadcast_templates` (registro)
Espelha os templates aprovados na Meta para o dashboard renderizar o form certo.
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `name` | str | igual ao nome na Meta |
| `language` | str | ex: `pt_BR` |
| `category` | str | `MARKETING \| UTILITY` |
| `variaveis` | JSONB | `[{indice:1, label:"Link do app", tipo:"url"}, ...]` |
| `header_tipo` | str \| null | `none \| image` |
| `ativo` | bool | |

Semeada com: *comunicado geral*, *promoção*, *lançamento de app*.

### Coluna nova em `clientes`
- `marketing_optout` (bool, default false)
- `marketing_optout_at` (datetime \| null)

Separado de `cobranca_optout`. Disparo de marketing **sempre** filtra `marketing_optout = false`.

---

## 2. Resolver de segmento (peça única, 3 usos)

`resolver_segmento(filtros) -> Select` monta a query base em `Cliente`:
- `deleted_at IS NULL`
- `marketing_optout = false`
- `whatsapp IS NOT NULL` (e não vazio)
- opcionais: `cidade == filtros.cidade`, `status == filtros.status`, `plano == filtros.plano`

A **mesma** função alimenta:
1. **Contagem** do preview (`SELECT count`)
2. **Export** CSV/Excel
3. **Lista de destinatários** do disparo (cria `campanha_destinatarios`)

Garante que "o que eu vi no preview = o que vou exportar = quem vai receber".

---

## 3. Fluxo de envio

```
[Admin] cria rascunho (canal cloud + template + variáveis + filtros)
   │
   ├─ Preview: "X clientes vão receber" + amostra (resolver_segmento → count)
   ├─ Teste: envia 1 msg do template pro número do admin
   │
   └─ Disparar:
        status → enviando
        enfileira send_campanha_task(id) na fila `notifications`
            ↓
        task:
          1. resolve segmento → cria campanha_destinatarios (pendente)
             (idempotente: pula quem já não está pendente)
          2. total_destinatarios = N
          3. para cada lote:
               adapter.send_template(...) via helper genérico extraído do notify_sender
               grava wamid + status=enviada (ou falha+erro), atualiza contadores
               pausa entre lotes (throttle por tier Meta)
          4. status → concluida (mesmo com falhas) / erro (falha catastrófica)
```

### Reaproveitamento do `notify_sender`
Extrair de `workers/notify_sender.py` um helper genérico (ex: `send_via_adapter(adapter, jid, ...)`) que: resolve/usa o adapter do canal, envia, trata retry/backoff e grava `WhatsAppMessageStatus`. O `notify_sender` passa a chamar esse helper; a task de campanha também. Sem duplicar a máquina de envio.

### Throttling
Respeita o tier da Meta (1k / 10k / 100k / ilimitado por 24h). Ritmo configurável (msgs/seg) com pausa entre lotes; erro 429 cai no backoff exponencial que o `CloudAdapter` já tem. Aviso de cap diário documentado.

### Webhook de status
O handler de status já existente atualiza `entregue`/`lida`/`falha` em `WhatsAppMessageStatus`; estende-se para também atualizar `campanha_destinatarios` localizando por `wamid`. Progresso da campanha fica vivo no dashboard.

### Tratamento de erros
- Falha de 1 cliente **não** aborta a campanha: registra `falha` + `erro` e segue.
- Canal não-cloud → rejeita na criação (validação).
- Template inexistente/variáveis incompletas → rejeita antes de disparar.
- Falha catastrófica (DB/broker) → campanha `erro`, destinatários pendentes preservados (retry idempotente).

---

## 4. Export

`GET /api/v1/admin/comunicados/export?cidade=&status=&plano=&format=csv|xlsx`
- Usa `resolver_segmento`.
- Descriptografa `nome` e `cpf_cnpj` (PII) — **só admin**.
- Stream sem gravar em disco: CSV via `csv.DictWriter` (`io.StringIO`), XLSX via `openpyxl` (`io.BytesIO`).
- Colunas: `nome`, `cpf_cnpj`, `whatsapp`, `cidade`, `plano`, `status`, `sgp_id`.
- `Content-Disposition: attachment`.
- Registro de **auditoria** (export de PII): quem, quando, filtros, qtd de linhas.

---

## 5. Dashboard — seção `/comunicados`

Estrutura Next.js seguindo o padrão existente (`app/(admin)/<dominio>/page.tsx` + componentes + React Query + `apiFetch`).

- **Lista de campanhas** (`/comunicados`): título, status, data, total, enviadas/entregues/lidas/falhas.
- **Nova campanha** (`/comunicados/nova`):
  1. Seleciona canal (Cloud)
  2. Seleciona template (dropdown lê `broadcast_templates`)
  3. Preenche variáveis — campos gerados pelo `variaveis` do template
  4. Define filtros (cidade / status / plano) ou marca "base inteira"
  5. **Contador ao vivo**: "X clientes vão receber" (chama `/preview`)
  6. Botões: **Exportar CSV** / **Exportar Excel**, **Enviar teste pro meu número**, **Disparar** (modal de confirmação mostrando o total)
- **Detalhe da campanha** (`/comunicados/[id]`): progresso + métricas em tempo real (polling React Query), lista de falhas.

---

## 6. API

Router novo `apps/api/src/ondeline_api/api/v1/comunicados.py`, prefixo `/api/v1/admin/comunicados`, todos `Depends(require_role(Role.ADMIN))`:

| Método | Rota | Função |
|---|---|---|
| GET | `/` | lista campanhas |
| POST | `/` | cria rascunho |
| GET | `/templates` | lista `broadcast_templates` ativos |
| POST | `/preview` | recebe filtros → contagem + amostra |
| POST | `/{id}/test` | envia teste pro número informado |
| POST | `/{id}/send` | valida + enfileira `send_campanha_task` |
| POST | `/{id}/cancel` | cancela (se ainda não concluída) |
| GET | `/{id}` | detalhe + progresso |
| GET | `/export` | CSV/XLSX do segmento |

Registrar o router no `main.py` (`app.include_router`).

---

## 7. Infra / workers / migrations

- **Celery:** task `send_campanha_task` em `workers/broadcast.py` (novo), registrada no `include` do `celery_app.py` (lembrete: task nova precisa entrar no include, senão o worker não a conhece). Roteada para a fila `notifications`.
- **Migration Alembic:** cria `campanhas`, `campanha_destinatarios`, `broadcast_templates` + coluna `marketing_optout`/`marketing_optout_at` em `clientes`. Seed dos 3 templates.
- **Config:** reaproveita `whatsapp_cloud_*`. Adiciona, se necessário, parâmetro de ritmo de envio (msgs/seg).

---

## 8. Testes

Escritos no código, **rodados na máquina de deploy** (não localmente):
- `resolver_segmento`: cada filtro isolado e combinados; exclui `deleted_at`, `marketing_optout`, whatsapp vazio.
- Export: serialização CSV e XLSX, colunas corretas, descriptografia.
- `send_campanha_task`: idempotência (re-rodar não redispara), contagem de enviadas/falhas, falha de 1 não aborta.
- Exclusão de opt-out de marketing no disparo.
- Validação: canal não-cloud rejeitado; template/variáveis incompletas rejeitadas.

---

## 9. Fora de escopo (extensões futuras)

- Agendamento real (`agendada_para` + beat task).
- Auto-opt-out por resposta "SAIR"/"PARAR".
- Submissão de templates novos via Graph API direto do dashboard.
- Métricas agregadas de campanha (taxa de entrega/leitura por período).

## 10. Pré-requisito operacional (Robert)

Cadastrar manualmente no WhatsApp Manager os 2-3 templates iniciais (comunicado geral, promoção, lançamento de app) e aguardar aprovação da Meta antes do primeiro disparo real. Passo-a-passo a ser fornecido na implementação.
