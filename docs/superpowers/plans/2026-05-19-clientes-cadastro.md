# Plano — Cadastro de Clientes em Campo (Flutter + Postgres)

**Data:** 2026-05-19
**Status:** ✅ Aprovado — pronto pra começar Fase 1

## Contexto

Roberto tem hoje um **site separado em MySQL** onde técnicos cadastram
clientes durante a instalação. O fluxo atual:

1. Técnico instala internet na casa do cliente
2. Abre o site (browser) e cadastra os dados
3. Esses dados depois vão pro SGP (separadamente, manual)

**Objetivo:** trazer esse cadastro pra dentro do app BlaBla Técnico
(Flutter) + Postgres do BlaBla, aposentando o site MySQL.

## Decisões consolidadas

| Decisão | Escolha |
|---|---|
| Site MySQL antigo | Aposentar (migração definitiva) |
| Tabela no Postgres | **Separada** (`clientes_cadastro`) da `clientes` (SGP/bot) |
| Cruzamento com `clientes` SGP | Por `cpf_hash` |
| `installer` | Auto-preenchido com técnico logado (FK + nome) |
| `plan_id` | Vem do SGP (`/api/ura/consultaplano/`) com cache Redis 1h |
| PII | Encrypted (Fernet) + hash (HMAC pepper) |
| Material consumido | **Lista do estoque do técnico** — marca itens + quantidades → baixa automática |
| Fotos | **Mín. 1** — sem 4 slots fixos. Lista flexível, qualquer foto |
| Sub-página dashboard | `/clientes/sgp` — listagem com badge "sincronizado / pendente" |
| Importação MySQL | Botão admin na `/clientes/sgp` (upload CSV/JSON) |
| Volume | ~1000 clientes (batch único, simples) |
| ViaCEP | Sim, autofill de endereço via API pública |
| Tabs no Flutter | 4 — OS / Estoque / Clientes / Perfil |

## Schema dos planos (confirmado)

```json
{
  "planos": [
    {
      "id": 15,
      "grupo": "fibra",
      "descricao": "NOVO PLANO 40MB 2026",
      "preco": 150.0,
      "download": 46080,   // Kbps
      "upload": 7168,      // Kbps
      "qtd_servicos": 14   // quantos clientes nesse plano
    }
  ]
}
```

---

## 1. Schema novo

### Migration `0023_clientes_cadastro`

```python
op.create_table(
    "clientes_cadastro",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("cpf_hash", sa.String(64), nullable=False),
    sa.Column("cpf_encrypted", sa.Text(), nullable=False),
    sa.Column("nome_encrypted", sa.Text(), nullable=False),
    sa.Column("dob", sa.Date(), nullable=False),
    sa.Column("telefone_encrypted", sa.Text(), nullable=False),
    # Endereço (texto plain — não é PII forte, fica searchable)
    sa.Column("cep", sa.String(10), nullable=True),
    sa.Column("address", sa.String(255), nullable=False),
    sa.Column("number", sa.String(10), nullable=False),
    sa.Column("complement", sa.String(255), nullable=True),
    sa.Column("neighborhood", sa.String(100), nullable=True),
    sa.Column("city", sa.String(100), nullable=False),
    sa.Column("state", sa.String(2), nullable=True),
    # Plano + conexão
    sa.Column("plan_id", sa.Integer(), nullable=True),   # ID do plano no SGP
    sa.Column("plan_nome", sa.String(255), nullable=False),
    sa.Column("pppoe_user_encrypted", sa.Text(), nullable=True),
    sa.Column("pppoe_pass_encrypted", sa.Text(), nullable=True),
    sa.Column("due_date", sa.Integer(), nullable=False),  # 1-28
    # Quem instalou
    sa.Column(
        "installer_user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("installer_nome", sa.String(255), nullable=False),
    # Equipamento + contrato
    sa.Column("serial", sa.String(100), nullable=True),
    sa.Column("contrato", sa.String(20), nullable=True),
    sa.Column("observation", sa.Text(), nullable=True),
    # Geo
    sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
    sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
    sa.Column("location_accuracy", sa.Numeric(10, 2), nullable=True),
    # Fotos (JSONB array de paths/metadata)
    sa.Column("fotos", postgresql.JSONB(), nullable=True),
    # Audit + sync
    sa.Column("registration_date", sa.Date(), nullable=False),
    sa.Column("sgp_synced_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("sgp_id", sa.String(40), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
)
op.create_index("ix_clientes_cadastro_cpf_hash", "clientes_cadastro", ["cpf_hash"], unique=True)
op.create_index("ix_clientes_cadastro_city", "clientes_cadastro", ["city"])
op.create_index("ix_clientes_cadastro_serial", "clientes_cadastro", ["serial"])
op.create_index("ix_clientes_cadastro_location", "clientes_cadastro", ["latitude", "longitude"])
op.create_index("ix_clientes_cadastro_installer", "clientes_cadastro", ["installer_user_id"])
op.create_index(
    "ix_clientes_cadastro_sync", "clientes_cadastro",
    ["sgp_synced_at"],  # filtros "pendente" usam IS NULL
)
```

### Link com estoque: `estoque_movimento.cliente_cadastro_id`

Adicionar coluna nullable em `estoque_movimento`:

```python
op.add_column(
    "estoque_movimento",
    sa.Column(
        "cliente_cadastro_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("clientes_cadastro.id", ondelete="SET NULL"),
        nullable=True,
    ),
)
op.create_index(
    "ix_estoque_mov_cliente_cadastro",
    "estoque_movimento", ["cliente_cadastro_id"],
)
```

Assim cada baixa de material vinculada a uma instalação fica rastreável.

### Diferenças vs schema MySQL antigo

- CPF deixa de ser PK (UUID interno é) — `cpf_hash` UNIQUE faz papel funcional
- PII encriptado (CPF, nome, telefone, PPPoE)
- `installer` virou FK + nome cacheado
- `plan_id` separado de `plan_nome` (link com SGP)
- `sgp_synced_at` + `sgp_id` pra rastrear sync
- `fotos` JSONB (lista de paths)
- `deleted_at` (soft delete)

---

## 2. Backend — Endpoints

### Catálogo + busca (técnicos + atendentes + admin)

```
GET  /api/v1/clientes-campo
     Query: q (nome/CPF/serial), city, sgp_status (synced|pending|all),
            installer_user_id, limit, cursor
     Roles: TECNICO, ATENDENTE, ADMIN
     Returns: lista paginada com campos descriptografados

GET  /api/v1/clientes-campo/{id}
     Returns: detalhe completo + lista de fotos + materiais usados

GET  /api/v1/clientes-campo/by-cpf/{cpf}
     Atalho — internamente hashea o cpf

GET  /api/v1/clientes-campo/{id}/ordens-servico
     JOIN com `ordens_servico` via cpf_hash → clientes
     Returns: lista de OS do mesmo CPF (se houver Cliente SGP)
```

### CRUD

```
POST /api/v1/clientes-campo
     Body: ClienteCadastroIn (sem installer) + materiais opcional
       {
         cpf, nome, dob, telefone, cep, address, ..., plan_id, plan_nome,
         pppoe_user, pppoe_pass, due_date, serial, contrato, observation,
         latitude, longitude, location_accuracy,
         materiais: [{item_id, quantidade, serial?}, ...]  // opcional
       }
     - installer_user_id = current_user.id
     - installer_nome = current_user.name
     - registration_date = today
     - Materiais: faz baixa atômica do estoque do técnico (saida com
       cliente_cadastro_id = novo cliente_id). Se saldo insuficiente,
       rollback total e 409.
     - Valida: CPF DV, due_date 1-28
     Roles: TECNICO, ATENDENTE, ADMIN

PATCH /api/v1/clientes-campo/{id}
     Body: campos editáveis
     - Tecnico edita: telefone, endereço, observação, lat/lng, fotos
     - Admin edita: tudo (exceto cpf_hash — pra trocar CPF cria novo)

DELETE /api/v1/clientes-campo/{id}
     Soft delete (deleted_at)
     Roles: ADMIN
```

### Fotos

```
POST /api/v1/clientes-campo/{id}/fotos
     Multipart upload (imagem)
     Body: file + tipo (opcional: "serial" | "instalacao" | "speedtest" | "outro")
     Salva em /tmp/ondeline_cliente_fotos/{cliente_id}/<uuid>.jpg
     Append em clientes_cadastro.fotos
     Returns: ClienteCadastroOut atualizado

DELETE /api/v1/clientes-campo/{id}/fotos/{foto_idx}
     Remove foto da lista + arquivo
     Roles: TECNICO (só as próprias), ATENDENTE, ADMIN
```

### Status SGP (admin)

```
POST /api/v1/clientes-campo/{id}/sync-sgp
     Marca como sincronizado. Body: { sgp_id: string }
     Grava sgp_synced_at = now, sgp_id = body.sgp_id
     Roles: ADMIN
     (Sync automático via API SGP fica pra outro PR)
```

### Importação MySQL

```
POST /api/v1/clientes-campo/import
     Multipart upload de CSV/JSON
     Body: arquivo + dry_run (bool)
     Roles: ADMIN
     - Dedup por cpf_hash (UPDATE se existe)
     - installer match: tenta achar user pelo nome, senão deixa só texto
     - Marca todos como sgp_synced_at = registration_date (vieram do MySQL,
       já estavam no SGP de alguma forma)
     - Encripta PII na inserção
     Returns: { ok: N, skipped: N, errors: [...] }
```

### Integração SGP — Planos

```
GET  /api/v1/sgp/planos
     Query: provider (ondeline | linknetam, default ondeline)
     Cache Redis 1h
     Returns: { planos: [{id, descricao, preco, download, upload, ...}] }
     Roles: TECNICO, ATENDENTE, ADMIN

Implementação:
async def listar_planos_sgp(session, redis, provider="ondeline"):
    cache_key = f"sgp:planos:{provider}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    cfg = await load_sgp_config(session, provider)
    r = await httpx.AsyncClient().post(
        f"{cfg['base_url']}/api/ura/consultaplano/",
        data={"app": cfg["app"], "token": cfg["token"]},
    )
    planos = r.json()["planos"]
    await redis.setex(cache_key, 3600, json.dumps(planos))
    return planos
```

---

## 3. Flutter — Nova aba "Clientes" (3ª no bottom nav)

### Bottom nav final

`OS / Estoque / Clientes / Perfil`

### Telas

**`/clientes` (lista)**
- Busca no topo (nome / CPF / cidade)
- Lista cards: nome + endereço + plano + cidade + badge "instalei eu" se
  installer_user_id == user atual
- FAB "+" → `/clientes/novo`
- Pull-to-refresh + cache Drift local

**`/clientes/:id` (detalhe)**
- Header: nome + CPF + foto (avatar de iniciais)
- Endereço com botão "Abrir no Maps"
- Plano + PPPoE (login/senha copiáveis)
- Status SGP: badge (verde "ativo" / amarelo "suspenso" / cinza "não no
  SGP") — consulta `clientes` por cpf_hash
- Materiais usados (lista, somente leitura)
- Galeria de fotos (tap pra fullscreen)
- Histórico de OS (lista clicável)
- Botão Editar

**`/clientes/novo` (form em 3 steps)**

*Step 1 — Dados pessoais:*
- CPF (validação live com DV)
- Nome
- Data nascimento (date picker)
- Telefone (máscara BR)

*Step 2 — Endereço + plano:*
- CEP → autofill via ViaCEP (https://viacep.com.br/ws/{cep}/json/)
- Endereço, número, complemento, bairro, cidade, estado
- Plano (dropdown carregado de `GET /api/v1/sgp/planos`)
  - Mostra: "PLANO 40MB · R$ 150 · 46 Mbps"
- PPPoE user/pass (gerados auto a partir do CPF, editáveis)
- Vencimento (1-28)

*Step 3 — Instalação:*
- Serial do equipamento (com scanner QR/code-bar — `mobile_scanner`?)
- Contrato (texto)
- Observação (textarea)
- **Materiais consumidos:** lista do estoque do técnico, com toggle
  on/off + quantidade. Pra item serializado, dropdown de seriais do
  estoque dele.
- **Fotos:** botão "+ Foto" abre câmera. Lista de thumbnails. Mín. 1.
- GPS capturado em background ao abrir step 3, mostra "GPS pronto ✓"
- Installer mostrado read-only (user logado)
- Botão Salvar

**Offline:** se sem conexão, enfileira na outbox como `kind: cliente_cadastro`.
Sync service envia depois (junto com fotos).

---

## 4. Dashboard — Páginas novas

### `/clientes` (admin/atendente)

Página de gestão geral. Tabs:

- **Em campo** — lista de `clientes_cadastro` (cadastrados pelo Flutter)
- **SGP** — sub-página `/clientes/sgp` (próximo bloco)

**Em campo:**
- Filtros: cidade, técnico instalador, período
- Tabela: CPF parcial / nome / endereço / plano / instalado por / data
- Clica em linha → detalhe (mesmo dialog ou nova página)
- Editar (admin) / Excluir (admin)

### `/clientes/sgp` (admin) — NOVA

**Listagem com status:**
- Tabela igual à de "Em campo" + coluna **Status SGP**:
  - 🟢 Sincronizado (tem `sgp_id` + `sgp_synced_at`)
  - 🟡 Pendente (sem `sgp_synced_at`)
- Filtro `?status=pending|synced|all`
- Ação por linha (admin): **"Marcar como sincronizado"** → modal pede
  `sgp_id`, grava `sgp_synced_at=now()`

**Botão "Importar do MySQL"** (canto superior direito):
- Modal com:
  - Upload de CSV (do `mysqldump --tab` ou export do site)
  - Botão "Dry run" (mostra o que vai importar sem gravar)
  - Botão "Importar de verdade"
- Chama `POST /clientes-campo/import` com dry_run
- Mostra resumo: N inseridos / N atualizados / N pulados / erros

---

## 5. Script de importação standalone (alternativa)

Pra Robert que tem credenciais MySQL na máquina:

```bash
python scripts/import_clientes_mysql.py \
  --mysql-url mysql://user:pass@host/db \
  --api-url https://apiblabla.robertbr.dev \
  --admin-token <token> \
  --dry-run
```

Conecta no MySQL, lê tudo, manda pra API em batches de 100. Vantagem:
credenciais MySQL nunca saem da sua máquina.

---

## 6. Material consumido — detalhes

### Fluxo

1. Técnico no step 3 do form vê: lista do estoque dele (consome
   `GET /api/v1/tecnico/me/estoque/saldo` que já existe)
2. Marca itens: 1× ONU XPON serial ABC123, 50m cabo, 4 conectores
3. Ao salvar:
   - Backend cria o cliente_cadastro
   - Em sequência (mesmo flush/transação), pra cada material:
     - `registrar_movimento(item_id, tipo=saida, quantidade, tecnico_id,
        cliente_cadastro_id, serial?, observacao="instalação cliente X")`
   - Se saldo insuficiente: 409 e **nada é gravado** (transação rollback)

### Item serializado (ONU/roteador)

- Dropdown mostra seriais que o técnico tem no estoque
  (consulta `/estoque/movimentos?tecnico_id=X&item_id=Y&serializado=true`)
- O serial selecionado vai também pro `clientes_cadastro.serial`
- O movimento de saída amarra: cliente_equipamento criada (já existe
  esse hook em `_atualizar_cliente_equipamento`) — mas hoje só dispara
  com `ordem_servico_id`. Vou estender pra disparar também com
  `cliente_cadastro_id`.

---

## 7. Roadmap de execução

| Fase | Entrega | Estimativa |
|---|---|---|
| 1 | Migration 0023 + modelo + repo Postgres | 2h |
| 2 | Endpoints CRUD básicos + sgp/planos | 3h |
| 3 | Endpoint `/import` + script Python | 2h |
| 4 | Endpoint de fotos + materiais (com baixa estoque atômica) | 3h |
| 5 | Tela Flutter de Clientes — lista + detalhe + busca | 3h |
| 6 | Tela de cadastro novo — form 3 steps + GPS + ViaCEP + planos SGP | 4h |
| 7 | Fotos no app (câmera + galeria, mín 1) | 2h |
| 8 | Materiais no app (lista do estoque + seleção) | 2h |
| 9 | Cache offline Drift + outbox para clientes_cadastro | 3h |
| 10 | Dashboard: páginas `/clientes` e `/clientes/sgp` + import UI | 4h |
| 11 | (Futuro PR) Sync automático pro SGP via API | separado |

**Total estimado:** ~28h de trabalho. Divido em 9-10 commits independentes.

---

## 8. Dependências/Riscos

- ✅ `/api/ura/consultaplano/` confirmado funcionando (JSON dado)
- ⚠️ ViaCEP API pública sem chave — pode rate-limit em pico mas raríssimo
- ⚠️ `mobile_scanner` pra ler serial QR — adicionar dep (Flutter)
- ⚠️ Volume de 1000 clientes na import — vou fazer em batches de 50
  pra não estourar timeout

---

## 9. Aprovação final

Confirmações de Robert recebidas:

- ✅ Plano OK em geral
- ✅ Schema dos planos SGP (JSON)
- ✅ ~1000 clientes no MySQL
- ✅ 4 tabs no Flutter
- ✅ ViaCEP pode usar
- ✅ Material = lista do estoque do técnico (baixa automática)
- ✅ Fotos = mín 1 (não 4 obrigatórias)
- ✅ Sub-página `/clientes/sgp` com filtro de status

**Pronto pra começar Fase 1.**
