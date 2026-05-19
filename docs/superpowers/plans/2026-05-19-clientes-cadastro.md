# Plano — Cadastro de Clientes em Campo (Flutter + Postgres)

**Data:** 2026-05-19
**Status:** ⏳ aguardando revisão e GO do Robert

## Contexto

Roberto tem hoje um **site separado em MySQL** onde técnicos cadastram
clientes durante a instalação. O fluxo atual:

1. Técnico instala internet na casa do cliente
2. Abre o site (browser) e cadastra os dados (nome, CPF, endereço, plano,
   PPPoE, GPS, etc)
3. Esses dados depois vão pro SGP (separadamente)

**Objetivo:** trazer esse cadastro pra dentro do app BlaBla Técnico
(Flutter) + Postgres do BlaBla, aposentando o site MySQL.

## Decisões já tomadas

| Decisão | Escolha |
|---|---|
| Site MySQL antigo | Aposentar (migração definitiva) |
| Tabela no Postgres | **Separada** da `clientes` (do SGP/bot) |
| Cruzamento entre as duas | Por `cpf_hash` quando o bot identificar via WhatsApp |
| `installer` | Auto-preenchido com o técnico logado (FK pra users + nome cacheado) |
| Lista de planos | Vem do SGP via `/api/ura/consultaplano/` (mesmo app+token de `/api/ura/clientes/`) |
| PII | Padrão do projeto: encrypted (Fernet) + hash (HMAC pepper) |
| Escopo Flutter | Buscar + Cadastrar + Ver OS do cliente |

## Por que tabela separada?

A tabela `clientes` existente é um **cache do SGP** — espelha o que está lá.
Já a tabela `clientes_cadastro` é **fonte primária da instalação** — gravada
pelo técnico em campo, com dados que o SGP não tem (lat/lng exata da
instalação, installer, observação de campo).

Quando o cliente entra em contato via WhatsApp e o bot identifica pelo CPF,
o sistema **cruza** `clientes_cadastro.cpf_hash` com `clientes.cpf_hash` e
mostra histórico unificado. Ambas as tabelas podem ter o mesmo CPF — não
são exclusivas.

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
    sa.Column("plan_id", sa.String(40), nullable=True),  # ID do plano no SGP
    sa.Column("plan_nome", sa.String(255), nullable=False),
    sa.Column("pppoe_user_encrypted", sa.Text(), nullable=True),
    sa.Column("pppoe_pass_encrypted", sa.Text(), nullable=True),
    sa.Column("due_date", sa.Integer(), nullable=False),  # 1-28 (dia do vencimento)
    # Quem instalou
    sa.Column(
        "installer_user_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("installer_nome", sa.String(255), nullable=False),  # cache
    # Equipamento + contrato
    sa.Column("serial", sa.String(100), nullable=True),
    sa.Column("contrato", sa.String(20), nullable=True),
    sa.Column("observation", sa.Text(), nullable=True),
    # Geo
    sa.Column("latitude", sa.Numeric(10, 8), nullable=True),
    sa.Column("longitude", sa.Numeric(11, 8), nullable=True),
    sa.Column("location_accuracy", sa.Numeric(10, 2), nullable=True),
    # Audit + sync
    sa.Column("registration_date", sa.Date(), nullable=False),
    sa.Column("sgp_synced_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("sgp_id", sa.String(40), nullable=True),  # ID retornado pelo SGP após sync
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
)
op.create_index(
    "ix_clientes_cadastro_cpf_hash", "clientes_cadastro",
    ["cpf_hash"], unique=True,
)
op.create_index("ix_clientes_cadastro_city", "clientes_cadastro", ["city"])
op.create_index(
    "ix_clientes_cadastro_city_name", "clientes_cadastro",
    ["city", "nome_encrypted"],
)
op.create_index(
    "ix_clientes_cadastro_serial", "clientes_cadastro", ["serial"]
)
op.create_index(
    "ix_clientes_cadastro_location", "clientes_cadastro",
    ["latitude", "longitude"],
)
op.create_index(
    "ix_clientes_cadastro_installer", "clientes_cadastro",
    ["installer_user_id"],
)
```

**Diferenças vs schema MySQL antigo:**
- CPF não é mais PK (UUID interno é) — `cpf_hash` UNIQUE faz o papel funcional
- CPF, nome, telefone, PPPoE encriptados (LGPD)
- `installer` virou FK + nome cacheado
- `plan_id` separado de `plan_nome` (link com SGP)
- `sgp_synced_at` + `sgp_id` pra rastrear sync

---

## 2. Backend — Endpoints

### Catálogo + busca

```
GET  /api/v1/clientes-campo
     Query: q (busca por nome/CPF/serial), city, limit, cursor
     Roles: TECNICO, ATENDENTE, ADMIN
     Returns: lista paginada (cursor) com campos descriptografados

GET  /api/v1/clientes-campo/{id}
     Roles: TECNICO, ATENDENTE, ADMIN
     Returns: detalhe completo

GET  /api/v1/clientes-campo/by-cpf/{cpf}
     Atalho pra busca por CPF (hash internamente)

GET  /api/v1/clientes-campo/{id}/ordens-servico
     JOIN com `ordens_servico` via cpf_hash → clientes.cpf_hash
     Retorna histórico de OS do mesmo CPF (se houver Cliente SGP)
```

### CRUD

```
POST /api/v1/clientes-campo
     Body: ClienteCadastroIn (sem installer — pego do user logado)
     Roles: TECNICO, ATENDENTE, ADMIN
     - installer_user_id = current_user.id
     - installer_nome = current_user.name (cache)
     - registration_date = today
     - Validações: CPF válido, due_date 1-28, plan_id existe no SGP

PATCH /api/v1/clientes-campo/{id}
     Body: campos editáveis (técnico não pode mudar CPF nem installer)
     - Tecnico edita: telefone, endereço, observação, lat/lng
     - Admin edita: tudo, exceto cpf_hash (precisa criar novo registro)

DELETE /api/v1/clientes-campo/{id}
     Roles: ADMIN only
     Soft delete (deleted_at column — adicionar na migration)
```

### Integração SGP

```
GET  /api/v1/sgp/planos
     Proxy pro `/api/ura/consultaplano/` do SGP Ondeline (e/ou LinkNetAM)
     Cache Redis 1h (planos mudam pouco)
     Returns: [{id, nome, velocidade, preco}, ...]
     Roles: TECNICO, ATENDENTE, ADMIN

POST /api/v1/clientes-campo/{id}/sync-sgp     [futuro, fora desse PR]
     Envia o cliente pro SGP (Ondeline), pega sgp_id, grava sgp_synced_at
```

### Importação

```
POST /api/v1/clientes-campo/import
     Multipart upload de CSV ou JSON
     Roles: ADMIN
     Body: arquivo + dry_run (bool — mostra o que vai importar sem gravar)
     Returns: {ok: N, skipped: N, errors: [...]}
     - Dedup por cpf_hash (se já existe, faz UPDATE)
     - installer match: tenta achar user pelo nome, senão deixa só texto
     - Encripta PII na inserção
```

Alternativamente: **script Python standalone** que Robert roda localmente:
```bash
python scripts/import_clientes_mysql.py \
  --mysql-url mysql://user:pass@host/db \
  --dry-run
```
Conecta no MySQL via pymysql, lê tudo, faz POST no endpoint
`/import` da API. Vantagem: credenciais MySQL nunca saem da máquina de
Robert.

---

## 3. Service: SGP planos

```python
# services/sgp_planos.py

async def listar_planos_sgp(
    session: AsyncSession,
    redis: Redis,
    provider: str = "ondeline",
) -> list[dict]:
    """Consulta /api/ura/consultaplano/ do SGP. Cache Redis 1h."""
    cache_key = f"sgp:planos:{provider}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    cfg = await load_sgp_config(session, provider)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{cfg['base_url']}/api/ura/consultaplano/",
            data={"app": cfg["app"], "token": cfg["token"]},
        )
        r.raise_for_status()
        planos = r.json()

    await redis.setex(cache_key, 3600, json.dumps(planos))
    return planos
```

---

## 4. Flutter — Nova aba "Clientes"

### Nav

Bottom nav agora com **4 tabs**: `OS / Estoque / Clientes / Perfil`
(perfil vira o 4º). Ou: substituir Perfil por Clientes e mover Perfil pra
um botão no AppBar. **Recomendação: 4 tabs.**

### Telas

**`/clientes` (lista)**
- Campo de busca no topo (nome, CPF, cidade)
- Lista paginada com cards: nome + endereço + plano + cidade + badge
  "instalei eu" se installer_user_id == user atual
- Botão FAB "+" → `/clientes/novo`
- Pull to refresh + cache Drift

**`/clientes/:id` (detalhe)**
- Header card: nome + CPF + foto (avatar de iniciais)
- Endereço completo (com botão "abrir no Maps")
- Plano + PPPoE (login/senha copiáveis)
- Status SGP: badge (verde "ativo" / amarelo "suspenso" / cinza "não está
  no SGP") — consulta `clientes` por cpf_hash em background
- Histórico de OS: lista com link pra detalhe da OS
- Botão "Editar" (técnico vê só campos editáveis)

**`/clientes/novo` (form)**
- Campos:
  - CPF (validação live com dígitos verificadores)
  - Nome
  - Data de nascimento (date picker)
  - Telefone (com máscara)
  - CEP → auto-busca endereço via ViaCEP (opcional, brasileiro)
  - Endereço, número, complemento, bairro, cidade, estado
  - Plano (dropdown carregado do SGP via `GET /api/v1/sgp/planos`)
  - PPPoE user/pass (auto-gerados ou manual)
  - Vencimento (dia, 1-28)
  - Serial do equipamento
  - Contrato
  - Observação
- GPS capturado **em background** ao abrir a tela; mostra ícone "GPS
  capturado ✓" quando pronto
- **Installer pré-preenchido** com user logado (read-only)
- Botão Salvar → POST → volta pra `/clientes/:id`
- Funciona offline: enfileira na outbox se sem conexão

### Cache Drift

Nova tabela local `clientes_cadastro_local` espelhando os campos. Same
padrão do `OsLocal`.

---

## 5. Importação do MySQL → Postgres

### Script `scripts/import_clientes_mysql.py`

```python
# Pseudocódigo
import asyncio, pymysql, httpx, sys

def main():
    args = parse()
    mysql_conn = pymysql.connect(args.mysql_url)
    rows = mysql_conn.cursor.execute("SELECT * FROM clients").fetchall()

    api = httpx.Client(base_url=args.api_url, headers={"Authorization": f"Bearer {args.admin_token}"})
    success, skipped, errors = 0, 0, []
    for row in rows:
        payload = {
            "cpf": row["cpf"],
            "nome": row["name"],
            "dob": str(row["dob"]),
            "telefone": row["phone"],
            "cep": row["cep"],
            "address": row["address"],
            "number": row["number"],
            "complement": row["complement"],
            "neighborhood": row["neighborhood"],
            "city": row["city"],
            "state": row["state"],
            "plan_nome": row["plan"],
            "pppoe_user": row["pppoe_user"],
            "pppoe_pass": row["pppoe_pass"],
            "due_date": row["due_date"],
            "installer_nome": row["installer"],  # texto livre
            "serial": row["serial"],
            "contrato": row["contrato"],
            "observation": row["observation"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "location_accuracy": row["location_accuracy"],
            "registration_date": str(row["registration_date"]),
        }
        if args.dry_run:
            print(f"would import: {row['cpf']} - {row['name']}")
            continue
        try:
            r = api.post("/api/v1/clientes-campo/import-one", json=payload)
            r.raise_for_status()
            success += 1
        except Exception as e:
            errors.append(f"{row['cpf']}: {e}")
    print(f"OK: {success}, skipped: {skipped}, errors: {len(errors)}")
```

Backend complementa com endpoint `POST /clientes-campo/import-one` (admin)
que aceita o payload em plain text e faz encryption + upsert.

---

## 6. Roadmap de execução

| Fase | Entrega | PRs |
|---|---|---|
| 1 | Migration + modelo + repo Postgres | 1 commit |
| 2 | Endpoints CRUD + busca + sgp/planos | 1 commit |
| 3 | Tela Flutter de Clientes (lista + detalhe + busca) | 1 commit |
| 4 | Tela de cadastro com GPS + ViaCEP + planos SGP | 1 commit |
| 5 | Cache offline Drift + outbox | 1 commit |
| 6 | Script de importação MySQL | 1 commit |
| 7 | (Futuro) Sync pro SGP via API | separado |

---

## 7. Riscos e perguntas em aberto

- ⚠️ **`/api/ura/consultaplano/` retorna o quê exatamente?** Preciso ver um
  exemplo de resposta (JSON) pra mapear o schema do dropdown. Robert
  consegue rodar uma vez e mandar o JSON?
- ⚠️ **CPF duplicado na importação**: hoje o MySQL tem CPF como PK, então
  não há duplicatas. Mas e se na hora de importar o CPF colide com um
  registro **da tabela `clientes` (do SGP)**? Resposta: tabelas são
  separadas, não há conflito. Só dentro de `clientes_cadastro` mesmo.
- ⚠️ **Volume de dados**: quantos clientes tem hoje no MySQL? Se for
  poucos milhares, importação roda em <30s. Se for >100k, vale fazer em
  batches.
- ⚠️ **Sync pro SGP**: fora do escopo desse PR, mas precisa definir
  depois — POST manual no SGP? API automática? Job assíncrono?

---

## 8. Confirmações que preciso do Robert

Antes de começar a codar:

1. ✅ Plano OK em geral?
2. ❓ Pode rodar `curl` no `/api/ura/consultaplano/` e mandar o JSON de
   resposta?
3. ❓ Quantos clientes no MySQL atual? (`SELECT COUNT(*) FROM clients`)
4. ❓ Tem certeza que quer 4 tabs no Flutter (Clientes vira 3º, Perfil
   vira 4º)? Ou prefere outra disposição?
5. ❓ ViaCEP pra autofill — pode usar (API pública grátis) ou pula?
