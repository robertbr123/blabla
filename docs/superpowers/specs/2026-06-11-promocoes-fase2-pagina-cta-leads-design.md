# Promoções Fase 2 — Página dedicada + Landing CTA + Leads

**Data:** 2026-06-11
**Status:** Design aprovado em conversa (parqueado — aguardando priorização). Decisões tomadas via brainstorming com Robert.

## Contexto

O sistema de Promoções (Bloco C) já existe em produção: CRUD na dashboard (preview, upload de imagem, gradientes, segmentação, agendamento, reordenação), carrossel "Pra você" na home do app cliente, e métricas de view/click/CTR. O que falta: página dedicada `/promocoes` no app, página de detalhe (landing CTA) rica, e captura de **leads** ("Tenho interesse") que a equipe trabalha na dashboard.

## Decisões do brainstorming

1. **Ação do CTA:** botão "Tenho interesse" registra **lead na dashboard** (não WhatsApp).
2. **Navegação:** link "Ver todas →" no cabeçalho da seção "Pra você" na home (sem aba nova na navbar).
3. **Conteúdo do detalhe:** campos novos `descricao_longa` + `regulamento` (sem destaque de urgência de validade; validade aparece discreta nas regras).
4. **Gestão de leads:** lista com workflow de status (`novo → contatado → convertido | descartado`), sem notificação em tempo real por ora.
5. **Entrega em 2 fatias:** Fatia 1 = API + dashboard; Fatia 2 = app Flutter.

## Design

### 1. Backend (API)

**Campos novos em `promocoes`** (migration nova):
- `descricao_longa` (Text, opcional) — parágrafos da landing
- `regulamento` (Text, opcional) — seção "Regras da promoção" expansível

**Tabela nova `promocoes_leads`:**
- `id`, `promocao_id` (FK), `cliente_app_user_id`, `contrato_id`, `nome_snapshot`, `telefone_snapshot` (snapshot pra equipe não cruzar com SGP na hora de ligar)
- `status`: `novo → contatado → convertido | descartado`
- `created_at`, `updated_at`
- **Unique** `(promocao_id, cliente_app_user_id)` — sem lead duplicado; segundo toque responde "já registrado"

**Endpoints novos:**
- `POST /cliente-app/promocoes/{id}/interesse` → cria lead (idempotente; retorna `{ok, ja_registrado}`)
- `GET /cliente-app/promocoes/{id}` → detalhe (com descrição/regulamento)
- `GET /admin/promocoes/leads` (filtros: promoção, status) — role ATENDENTE+
- `PATCH /admin/promocoes/leads/{id}` (mudar status) — role ATENDENTE+

### 2. Dashboard

- Form de promoção: + textarea "Descrição completa" e "Regulamento" (opcionais; promo sem descrição continua funcionando, detalhe mostra subtítulo).
- **Aba "Leads"** na página de promoções: tabela nome / telefone / contrato / promoção / data / status, dropdown pra mudar status, filtros por promoção e status. Cards de resumo: leads novos, taxa de conversão.
- Métrica nova por promoção na lista existente: contagem de **leads** ao lado de views/clicks/CTR.

### 3. App Flutter

- **Rotas novas:** `/promocoes` (lista) e `/promocoes/:id` (detalhe).
- **Home:** cabeçalho "Pra você" ganha "Ver todas →" (só com 2+ promos).
- **Lista:** cards verticais reaproveitando `_PromoCard` extraído pra widget compartilhado (paga dívida de quebra). Empty state amigável.
- **Detalhe (landing CTA):**
  - Hero no topo com gradiente/imagem (hero animation a partir do card)
  - Título grande + subtítulo + descrição longa
  - "Regras da promoção" expansível (se houver regulamento); validade discreta ali
  - **Botão fixo no rodapé "Tenho interesse"** → registra lead → vira estado de sucesso "✓ Recebemos! Logo entramos em contato" (persistente entre aberturas)
  - Promo tipo `indicacao` ou com `cta_action` de tela/URL: botão executa a ação original em vez de gerar lead
  - Tracking: evento `detail_view` em `promocoes_eventos`

### 4. Erros e segurança

- Falha de rede no lead: botão volta ao normal + snackbar "Não conseguimos registrar, tenta de novo" (lead é dado de negócio, não é fire-and-forget como analytics).
- Endpoint de interesse autenticado (mesmo guard das rotas cliente-app); dedup pela unique constraint.

### 5. Testes

Testes de API pros endpoints de lead (criação, dedup, transição de status) na máquina de deploy + smoke manual no app. CI gate normal.
