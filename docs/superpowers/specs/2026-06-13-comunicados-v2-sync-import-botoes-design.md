# Comunicados v2 — Sync de templates, import de lista, botões e filtros dinâmicos

**Data:** 2026-06-13
**Status:** Aprovado (aguardando review do spec)
**Base:** evolui o sistema de Comunicados v1 (`2026-06-13-comunicados-disparo-massa-whatsapp-design.md`).

## Contexto e problema

O Comunicados v1 entregou disparo em massa segmentado + export. Uso real revelou 4 limitações:

1. **Filtros são campo livre** — digitar "Suspenso" errado não casa nada. Deveriam ser listas com os valores que existem na base.
2. **Não dá pra disparar pra quem não está na base** — muitos clientes nunca entraram em contato; o provedor tem a lista (telefone, etc.) fora do sistema e quer importar.
3. **Templates simples demais** — sem botões (ex: botão "Baixar app").
4. **Preso a 3 templates fixos (seed)** — se cadastrar um novo na Meta, não aparece pra disparar.

## Decisões aprovadas

1. **Templates: sync da Meta + cadastro manual ("os dois").** Sync puxa via Graph API; cadastro manual cobre ajustes pontuais.
2. **Sync só dos canais Cloud ATIVOS** (`provider=cloud AND ativo=true`). Robert tem >1 WABA mas só 1 ativo. Multi-WABA simultâneo = futuro.
3. **Import via CSV:** coluna de telefone obrigatória + colunas opcionais por variável (personalização por contato), com fallback pro valor padrão do formulário.
4. **Filtros = dropdown** com valores distintos da base.
5. **Botões:** estático (link fixo no template) não precisa de nada; dinâmico (URL com variável) recebe valor no disparo.
6. **CSV:** aceita separador `,` e `;` (autodetect).

---

## Bloco A — Filtros como dropdown

**Endpoint:** `GET /api/v1/admin/comunicados/segmento/valores`
Retorna `{ cidades: [...], status: [...], planos: [...] }` — valores distintos, não-nulos, de `clientes` com `deleted_at IS NULL`, ordenados.

**Dashboard:** os 3 campos do formulário viram `<select>` populados por esse endpoint, com opção "Todos" (= sem filtro). Mantém a semântica do `resolver_segmento` (vazio = base inteira).

---

## Bloco B — Templates: sync da Meta + manual

### Estrutura ampliada (`broadcast_templates`)
Passa a guardar a estrutura completa do template:
- `variaveis` (já existe): `[{indice, label, tipo}]`
- `header_tipo` (já existe): `none | image`
- **`botoes` (novo, JSONB):** `[{index, tipo, texto, url_dinamica}]` onde `tipo ∈ {url, quick_reply, phone}` e `url_dinamica` indica se a URL tem variável (`{{1}}`).

### Sync da Meta
**Endpoint:** `POST /api/v1/admin/comunicados/templates/sincronizar`
1. Busca todos os `Canal` com `provider='cloud' AND ativo=true`.
2. Para cada um, chama a Graph API `GET /{cloud_waba_id}/message_templates` (token global `whatsapp_cloud_access_token`, versão `whatsapp_cloud_graph_version`).
3. Filtra `status == "APPROVED"`.
4. Parseia `components`:
   - **BODY** → conta `{{1}}..{{n}}` no texto → `variaveis` (label default `Variável N`, tipo `texto`).
   - **HEADER** → `format == IMAGE` → `header_tipo="image"`, senão `"none"`.
   - **BUTTONS** → cada botão → `{index, tipo, texto, url_dinamica}` (url_dinamica = url contém `{{`).
5. **Upsert** por `name` (mantém o unique atual). Marca `ativo=true`.
6. Retorna `{ sincronizados: N, canais: M }`.

Service novo `services/whatsapp_templates_sync.py` (parse dos components) + função de cliente Graph `list_message_templates(waba_id, access_token, graph_version) -> list[dict]` (em `adapters/whatsapp/cloud.py`, usa httpx, com retry/backoff como o resto do adapter).

### Cadastro/edição manual
- `POST /api/v1/admin/comunicados/templates` — cria (name, language, category, variaveis, botoes, header_tipo, ativo).
- `PUT /api/v1/admin/comunicados/templates/{id}` — edita.
- Validação: `name` único; reaproveita o `BroadcastTemplateOut`/schema.

> Sync e manual escrevem na **mesma** tabela. O sync sobrescreve campos do template ao reimportar (fonte de verdade = Meta quando sincronizado).

---

## Bloco C — Disparo com botões

### Adapter
`CloudAdapter.send_template` ganha parâmetro opcional `button_url_param: str | None`. Quando setado (botão URL **dinâmico**, índice 0), adiciona ao payload:
```json
{"type": "button", "sub_type": "url", "index": "0",
 "parameters": [{"type": "text", "text": "<button_url_param>"}]}
```
Botão **estático** (URL fixa aprovada no template) não envia nada — já renderiza. Mantém `body_params` e `header_media_url` como hoje.

### broadcast_sender
`enviar_destinatario` resolve os parâmetros por destinatário:
- `body_params = destinatario.body_params or campanha.body_params`
- `button_param = destinatario.button_param or campanha.button_param`
e chama `send_template(..., body_params=..., header_media_url=campanha.header_media_url, button_url_param=button_param)`.

### Dashboard
Se o template selecionado tiver botão com `url_dinamica=true`, o formulário mostra um campo "Valor do botão (link)".

---

## Bloco D — Importar lista (CSV)

### Endpoint
`POST /api/v1/admin/comunicados/{id}/destinatarios/importar` (multipart, arquivo CSV; admin).
1. Lê o CSV (autodetect `,`/`;`, UTF-8 com/sem BOM).
2. Identifica a coluna de **telefone** (header `telefone|whatsapp|phone|celular`, case-insensitive; senão a 1ª coluna).
3. Para cada linha:
   - **Normaliza o telefone** (reuso de `utils/phone.py` do projeto) pro formato E.164 BR (`55` + DDD + número). Linha sem telefone válido → contabilizada como inválida, pulada.
   - Mapeia colunas cujo header casa com uma **variável do template** (por label normalizado ou `var1`,`var2`...) → monta `body_params` (ordenado por índice) daquela linha. Variável sem coluna → fica `None` (usa o default da campanha no envio).
   - Coluna `botao`/`link` (se existir) → `button_param` da linha.
   - Cria `CampanhaDestinatario` (`cliente_id=NULL`, `whatsapp`, `body_params` override, `button_param`, `status="pendente"`).
4. Marca `campanha.origem="importado"`, atualiza `total_destinatarios`.
5. Retorna `{ importados: N, invalidos: K, amostra_invalidos: [...] }`.

### Disparo de campanha importada
O `send_campanha_task` já materializa destinatários quando existem; para origem importada, os destinatários **já foram criados** pelo import, então a materialização por segmento é pulada (guard: se já há destinatários, não resolve segmento — já é o comportamento idempotente atual). O envio usa os params por destinatário (Bloco C).

### Dashboard
No formulário de campanha, escolha de **origem**: "Segmento da base" (filtros) **ou** "Importar CSV" (upload). Mostra contagem importados/inválidos.

---

## Mudanças de dados (migration 0050)

- `broadcast_templates`: + `botoes` JSONB `server_default '[]'`.
- `campanha_destinatarios`:
  - `cliente_id` → **nullable** (contatos importados não têm cadastro).
  - + `body_params` JSONB nullable (override por contato).
  - + `button_param` Text nullable.
- `campanhas`:
  - + `origem` String(12) `server_default 'segmento'`.
  - + `button_param` Text nullable (valor padrão do botão dinâmico).

ORM atualizado nos modelos correspondentes.

---

## API (resumo dos endpoints novos/alterados)

| Método | Rota | Função |
|---|---|---|
| GET | `/api/v1/admin/comunicados/segmento/valores` | valores distintos (cidade/status/plano) |
| POST | `/api/v1/admin/comunicados/templates/sincronizar` | sync da Meta (canais Cloud ativos) |
| POST | `/api/v1/admin/comunicados/templates` | cadastro manual |
| PUT | `/api/v1/admin/comunicados/templates/{id}` | edição manual |
| POST | `/api/v1/admin/comunicados/{id}/destinatarios/importar` | upload CSV |

`BroadcastTemplateOut` ganha `botoes`. `CampanhaCreate` ganha `origem` e `button_param`. `CampanhaDetail` reflete os novos campos.

---

## Dashboard (resumo)

- Filtros do formulário viram `<select>` (hook `useSegmentoValores`).
- Tela/aba de **Templates**: lista + botão "Sincronizar com a Meta" + formulário de cadastro/edição manual.
- Formulário de campanha: toggle **origem** (Segmento | Importar CSV); upload de CSV com retorno de importados/inválidos; campo de **valor do botão** quando o template tem botão dinâmico.
- Tipos/hooks novos em `lib/api`.

---

## Testes (escritos; rodam no CI/deploy)

- `segmento/valores`: distintos corretos, ignora nulos e deletados.
- Sync: parse de components (body→variáveis, header→tipo, buttons→botoes, url dinâmica vs estática), filtro APPROVED, só canais ativos, upsert idempotente (mock da Graph API).
- Adapter `send_template` com `button_url_param`: monta componente de botão certo; sem param não adiciona.
- broadcast_sender: usa params por destinatário quando presentes, senão os da campanha.
- Import CSV: autodetect separador; normalização de telefone (válidos/inválidos); mapeamento de colunas→variáveis; fallback; contagem de inválidos; `cliente_id` nulo.
- Disparo de campanha importada não re-materializa por segmento.

## Fora de escopo (futuro)

- Multi-WABA simultâneo no sync (hoje só os ativos; assume 1 ativo).
- Submeter templates NOVOS pra aprovação da Meta via API (hoje: criar na Meta manualmente OU cadastrar manual no dashboard).
- Botão dinâmico em índice != 0 / múltiplos botões dinâmicos (hoje: 1 botão URL dinâmico no índice 0).
- Agendamento e auto-opt-out (herdados do v1).
