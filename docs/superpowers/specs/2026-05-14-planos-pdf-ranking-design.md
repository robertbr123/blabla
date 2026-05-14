# Design Spec: Gestão de Planos, PDF de OS, Ranking de Técnicos

**Data:** 2026-05-14  
**Status:** Aprovado

---

## 1. Gestão de Planos (CRUD)

### Objetivo
Substituir o editor JSON raw por uma interface de cards com modal, permitindo criar, editar e excluir planos de forma visual e segura.

### Schema por Plano

```typescript
interface Plano {
  nome: string        // ex: "Plus"
  preco: number       // ex: 130.0
  velocidade: string  // ex: "55MB"
  extras: string[]    // ex: ["IPTV gratis", "câmera comodato"]
  descricao: string   // texto livre para o bot usar ao apresentar o plano
  ativo: boolean      // false = bot não apresenta, admin pode ocultar sem excluir
  destaque: boolean   // true = card com borda destacada, bot cita como recomendado
}
```

### Armazenamento
- Continua como JSONB na tabela `config` com chave `"planos"`.
- Não requer migração de banco.
- Os endpoints leem/escrevem o array completo atomicamente via `ConfigRepo`.

### Backend — Novos Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/api/v1/planos` | Público | Lista planos (bot + UI) |
| `POST` | `/api/v1/planos` | ADMIN | Cria novo plano |
| `PATCH` | `/api/v1/planos/{index}` | ADMIN | Edita plano pelo índice no array |
| `DELETE` | `/api/v1/planos/{index}` | ADMIN | Remove plano pelo índice |

- `GET /api/v1/planos` retorna todos os planos (ativos e inativos para admin; somente ativos para o bot via `consultar_planos` tool).
- A tool `consultar_planos` será atualizada para filtrar `ativo=true` e indicar `destaque=true` no texto.

### Frontend — Nova Página `/configuracoes/planos`

**Componentes:**
- `PlanosManager` — página principal com lista de cards
- `PlanoCard` — card individual com nome, preço, velocidade, descrição, badges (ativo, destaque), botões editar/excluir
- `PlanoModal` — modal de criação/edição com campos:
  - Nome, Preço (R$), Velocidade
  - Descrição (textarea)
  - Extras: chips removíveis + input para adicionar novo extra
  - Toggle Ativo / Toggle Destaque
- Confirmação de exclusão antes de deletar

**UX:**
- Card com borda amarela/ouro para plano com `destaque=true`
- Badge "inativo" em cinza para planos com `ativo=false`
- Botão "+ Novo Plano" no topo direito
- Toast de sucesso/erro após cada operação

---

## 2. PDF de Ordem de Serviço

### Objetivo
Gerar PDF de qualquer OS no backend, disponível para download no dashboard e para envio direto ao técnico via WhatsApp.

### Biblioteca
**WeasyPrint** — converte HTML+CSS para PDF no backend Python. Não requer Chrome/headless browser. Fits na stack FastAPI existente.

### Backend — Novos Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/api/v1/os/{os_id}/pdf` | ADMIN, ATENDENTE | Gera e retorna PDF da OS |
| `POST` | `/api/v1/os/{os_id}/enviar-pdf-tecnico` | ADMIN, ATENDENTE | Gera PDF + envia ao técnico via Evolution WhatsApp |

### Geração do PDF

**Fluxo:**
1. Endpoint busca OS + dados do cliente (descriptografados) + dados do técnico
2. Template Jinja2 renderiza HTML com os dados
3. WeasyPrint converte HTML → PDF em memória (BytesIO)
4. Fotos lidas do filesystem e embutidas como `data:image/jpeg;base64,...`
5. `GET` retorna `StreamingResponse` com `Content-Type: application/pdf`
6. `POST enviar-pdf-tecnico` salva PDF em `/tmp`, chama Evolution API para enviar como documento WhatsApp, depois deleta o arquivo

**Localização do template:** `apps/api/src/ondeline_api/templates/os_pdf.html`

### Conteúdo do PDF

**Página 1 — Dados:**
- Header: logo/nome Ondeline + código OS + data de criação
- Grid 2 colunas: Cliente (nome, telefone) | Técnico (nome, telefone)
- Bloco endereço
- Bloco problema (destaque amarelo)
- Badges: Status · Agendamento · Data de conclusão
- CSAT (se disponível): estrelas + comentário do cliente

**Página 2 — Fotos (omitida se não houver fotos):**
- Grid 2 colunas de fotos
- Cada foto com timestamp abaixo

### Frontend

Na página de detalhe da OS (`os-detail.tsx`), dois botões adicionais:
- **"Baixar PDF"** → abre `GET /api/v1/os/{id}/pdf` em nova aba
- **"Enviar PDF ao Técnico"** → chama `POST /api/v1/os/{id}/enviar-pdf-tecnico`, exibe toast de sucesso/erro

Botões visíveis para ADMIN e ATENDENTE. "Enviar PDF" desabilitado se a OS não tiver técnico atribuído.

---

## 3. Ranking de Técnicos

### Objetivo
Página dedicada no dashboard com ranking mensal de técnicos por OS concluídas, CSAT médio e tempo médio — para cálculo de pagamento e monitoramento de desempenho. Com exportação CSV.

### Backend — Novos Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/api/v1/metricas/tecnicos` | ADMIN, ATENDENTE | Ranking de técnicos com filtro por mês |
| `GET` | `/api/v1/metricas/tecnicos/export` | ADMIN, ATENDENTE | Exporta ranking como CSV |

**Query params:** `?mes=2026-05` (default: mês atual no formato `YYYY-MM`)

**Response `GET /api/v1/metricas/tecnicos`:**
```typescript
interface RankingTecnico {
  tecnico_id: string
  nome: string
  os_concluidas: number      // count WHERE status=CONCLUIDA E concluida_em no mês
  csat_avg: number | null    // AVG(csat) para OS concluídas com csat not null
  tempo_medio_min: number | null  // AVG em minutos de (concluida_em - criada_em)
  ultima_os_em: string | null    // ISO datetime da última OS concluída
}
// Ordenado por os_concluidas DESC
```

**CSV Export:** colunas `Técnico,OS Concluídas,CSAT Médio,Tempo Médio (min),Mês`

**Query SQL (lógica):**
```sql
SELECT
  t.id, t.nome,
  COUNT(os.id) AS os_concluidas,
  AVG(os.csat) AS csat_avg,
  AVG(EXTRACT(EPOCH FROM (os.concluida_em - os.criada_em)) / 60) AS tempo_medio_min,
  MAX(os.concluida_em) AS ultima_os_em
FROM tecnicos t
LEFT JOIN ordens_servico os ON os.tecnico_id = t.id
  AND os.status = 'CONCLUIDA'
  AND DATE_TRUNC('month', os.concluida_em) = DATE_TRUNC('month', :mes)
WHERE t.ativo = true
GROUP BY t.id, t.nome
ORDER BY os_concluidas DESC
```

### Frontend — Nova Página `/tecnicos/ranking`

**Componentes:**
- `RankingTecnicos` — página com tabela + controles
- Filtro de mês: `<input type="month">` (default: mês atual)
- Botão "Exportar CSV" — dispara download do CSV
- Tabela com colunas: `#` (medalha 🥇🥈🥉 para top 3) · Técnico · OS Concluídas · CSAT Médio · Tempo Médio
- Rodapé com total de OS no período

**Acesso:** ADMIN e ATENDENTE. Link no menu lateral abaixo de "Configurações".

---

## Ordem de Implementação Sugerida

1. **Gestão de Planos** — backend (endpoints + schema) → frontend (página + modal)
2. **Ranking de Técnicos** — backend (query + endpoints) → frontend (página + tabela + CSV)
3. **PDF de OS** — instalar WeasyPrint → template → endpoints → frontend (botões)

O PDF fica por último pois depende de dependência externa (WeasyPrint) que pode exigir ajustes no ambiente.

---

## Considerações Técnicas

- **WeasyPrint** requer `libpango` e `libcairo` no sistema. No Docker, adicionar ao `Dockerfile`: `apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0`
- **Fotos no PDF**: lidas do filesystem local (`/tmp/ondeline_os_fotos/`). Em produção, garantir que o container da API tem acesso ao volume de fotos.
- **Planos**: o índice `{index}` nos endpoints PATCH/DELETE refere-se à posição no array JSON. A operação é: ler array → modificar posição → salvar array completo.
- **Ranking CSV**: gerado com `csv.writer` do stdlib Python, retornado como `StreamingResponse` com `Content-Disposition: attachment`.
