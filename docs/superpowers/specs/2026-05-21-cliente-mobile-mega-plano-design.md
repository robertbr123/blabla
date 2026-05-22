# Cliente Mobile — Mega Plano de Evolução

**Data:** 2026-05-21 (atualizado 2026-05-22)
**App alvo:** `apps/cliente-mobile` (Flutter)
**Stack:** Flutter 3.27+ · Riverpod · go_router · Dio · FastAPI backend · Next.js dashboard
**Objetivo:** Transformar o app cliente atual num app de provedor de internet completo, moderno, com sistema de promoções gerenciável pelo dashboard.

---

## 📊 Status (snapshot 2026-05-22)

### ✅ Entregue
- **A1** Navbar flutuante com badges (faturas vencidas + OS abertas)
- **A2** Login + Onboarding glassmorphism (fundo animado + cards de vidro)
- **A3** Home redesenhada (hero, status pill, carrossel, quick actions coloridas)
- **A4** Faturas + QR Pix in-app (timeline, hero, qr_flutter)
- **A5** Perfil moderno (avatar gradient, cards, segmented dark/claro/auto)
- **A6 (parcial)** Tokens novos (motion, gradients, elevations, cores categóricas, Plus Jakarta Sans)
- **Bloco C completo (C.1 → C.5)** Sistema de promoções fim-a-fim:
  - C.1 backend (tabelas, endpoints cliente+admin, upload imagem)
  - C.2 dashboard `/admin/promocoes` (CRUD, preview, métricas, drag-drop, 5 templates seed)
  - C.3 app carrossel real consumindo API
  - C.4 integração Indicação (endpoint `/indicacao/meu`, tela in-app, share WhatsApp)
  - C.5 promoção tipo indicação ligada + banner em `/admin/indicacoes` + stats por origem
- **B1 (MVP)** Status do contrato (`/cliente-app/conexao` deriva ativo/suspenso/cancelado do SGP, sem telemetria PPPoE)
- **B4 (parcial)** Pagamentos expandido — filtro por ano nas pagas + share nativo Pix/boleto (`share_plus`)
- **B5** Central de notificações (tabelas, endpoints, sino com badge, tela list, tela preferências)
- **B5 triggers** Notificações automáticas: OS criada/atualizada, promo ativada (broadcast), manutenção (broadcast)
- **B6** Indique e ganhe (entregue via C.4 + C.5)
- **B10** FAQ in-app (11 artigos em 4 categorias, busca, atalho no Suporte)

### 🚧 Aberto
- **A6 (resto)** Dark mode polish em todas as telas (review tela-a-tela), acessibilidade WCAG, gradients reutilizáveis
- **B1 (telemetria real)** PPPoE up/down, uptime, sinal óptico — depende do adapter SGP expor
- **B2** Diagnóstico guiado (wizard "Sua internet caiu?" + reiniciar conexão remoto)
- **B3** Speedtest in-app
- **B4 (resto)** Promessa de pagamento (OS especial com data futura)
- **B5.2** Cron de faturas vencendo (notif automática diária)
- **B5 push real** Firebase Messaging out-of-app (token já existe em `cliente_app_user.push_token`)
- **B5 broadcast por cidade** Manutenção só pra clientes da região (join com SGP)
- **B7** Mudança de plano self-service
- **B8** Chat polish (WebSocket pra real-time, indicador "digitando…", anexo de foto) — handoff bot↔atendente já existe
- **B9** Banner de manutenção programada na home (notif já manda — falta banner inline)
- **Bloco D** Analytics, Sentry mobile, i18n PT/EN, acessibilidade

### 📝 Notas operacionais
- Migration 0034 (notif) precisou de `exec_driver_sql` pro JSONB default — `sa.text(":true")` quebra (interpretado como bind param).
- Promoções servem imagem em `/static/promocoes/` → `/tmp/ondeline_promocoes` (volume `/tmp` evita PermissionError).
- Indicação tem 2 contadores distintos: `IndicacaoUso.origem` (lead concreto) vs `Indicacao.shares_app` (compartilhamentos via app).
- Tipo `indicacao` de promoção força CTA = `tela:/indicacao` no validator.
- 5 templates prontos de promoção via `POST /api/v1/admin/promocoes/seed-templates` (idempotente).

---

## Estado atual (baseline)

Features já entregues:
- Onboarding por CPF + OTP + biometria
- Login com senha
- Home: hero card + quick actions + avisos
- Faturas: listagem + bottom sheet com Pix/boleto
- Suporte: OS + chat
- Perfil: editar dados, mudar senha
- Cor ciano/azul-marinho (`brand_tokens.dart`) alinhada com a logo
- Push (Firebase Messaging) opcional
- Cache last-known pra dados críticos

Pontos a melhorar:
- Visual genérico (Material padrão), pouca personalidade
- Navbar simples sem destaque ou badges
- Login/onboarding visualmente fracos
- Sem sistema de promoções
- Sem status de link em tempo real
- Sem diagnóstico self-service

---

## Ordem de execução

Fases incrementais. **Começamos por A1+A2+A3** (modernização visual core). Depois C (promoções fim-a-fim). Depois restante visual (A4/A5/A6) e features pesadas (B1–B10) na ordem de impacto.

---

## BLOCO A — Modernização visual

### A1. Navbar repaginada
- Substituir `NavigationBar` padrão por barra **flutuante** (margem lateral, cantos arredondados ~24px, sombra suave).
- Ícone central destacado tipo FAB elevado (ação principal: "Pagar agora" se houver fatura aberta, senão "Falar conosco").
- Animação na troca de tab (scale + fade no ícone selecionado).
- **Badges**:
  - Suporte: nº de chamados abertos ou mensagens não lidas no chat.
  - Faturas: ponto vermelho se há fatura vencida.
- Selected state com fundo pill ciano translúcido + label sempre visível.

### A2. Login + Onboarding glassmorphism
- Fundo gradiente animado (ciano → marinho) com 2-3 blobs orgânicos em loop lento (CustomPainter ou `AnimatedContainer`).
- Card central com `BackdropFilter` (vidro fosco), borda translúcida 1px branca/20%.
- Inputs com label flutuante (sobe ao focar), borda ciano no foco, micro-bounce.
- Botão primário com gradient + sombra colorida + `HapticFeedback.mediumImpact` no tap.
- Ilustração no topo: ícone wifi/antena animado em Lottie (ou SVG estático se evitar dependência).
- Aplicar mesmo tratamento em: `/login`, `/onboarding/cpf`, `/onboarding/otp`, `/onboarding/password`, `/onboarding/biometric`.

### A3. Home redesenhada
- **Hero card**:
  - Manter gradient atual mas adicionar "noise/grain" sutil ou shape geométrica de fundo.
  - Badge de **status do link** (placeholder enquanto B1 não vem): bolinha pulsante verde/amarela/vermelha + texto "Conexão estável".
  - Avatar/iniciais do cliente no canto.
- **Carrossel de promoções** (placeholder que renderiza lista vazia até C ficar pronto) — entre hero e quick actions.
- **Quick actions**:
  - Ícones coloridos (cada um com sua cor de "categoria"), não todos monocromáticos.
  - Cards com sombra suave + hover/pressed state convincente.
  - Skeleton com shimmer enquanto carrega.
- **Avisos**: manter mas melhorar visual (ícone por severidade, animação de entrada).
- Espaçamento, tipografia e ritmo vertical revisados.

### A4. Faturas (pós A1-A3)
- Timeline vertical das últimas 6 faturas com status colorido.
- Bottom sheet com QR code Pix renderizado in-app + botão "copiar Pix" gigante.
- Filtro por ano.

### A5. Perfil (pós A1-A3)
- Avatar circular (foto ou iniciais com cor gerada do nome).
- Cards agrupados: Dados / Segurança / Notificações / Sobre.
- Toggle dark mode visível.
- Link "Indique e ganhe" (placeholder até B6).

### A6. Tokens + tipografia
- Adicionar fonte `Plus Jakarta Sans` ou `Manrope` via google_fonts.
- Tokens novos em `brand_tokens.dart`:
  - `elevation1/2/3` (sombras)
  - `motionFast/Medium/Slow` (durações)
  - `gradientPrimary`, `gradientHero` reutilizáveis
  - `radiusXl` (24px), `radius2xl` (32px) pra cards flutuantes
- Tema dark polido em todas as telas.

---

## BLOCO B — Novas features

### B1. Status do link real-time ⭐
- API: `GET /api/cliente-app/conexao/status` retorna `{online: bool, ultima_queda: datetime?, uptime_min: int, sinal_optico_db: float?}` consultando SGP/equipamento.
- Widget no hero da home + tela dedicada com gráfico de uptime das últimas 24h.
- Push automático se cair > 5min.

### B2. Diagnóstico guiado
- Wizard "Sua internet caiu?": passos visuais (ver luzes do roteador, reiniciar, testar cabo).
- Se persistir, abre OS automaticamente pré-preenchida.
- Botão "Reiniciar minha conexão remotamente" (API derruba PPPoE via SGP) — gera OS de auditoria.

### B3. Speedtest in-app
- Pacote `flutter_internet_speed_test` ou implementação custom contra servidor próprio.
- Compara com plano contratado, salva histórico no backend.
- Dashboard admin vê média da base.

### B4. Pagamentos in-app expandido
- QR code Pix renderizado no app (sem precisar abrir PDF).
- Histórico de pagamentos completo com filtro.
- Promessa de pagamento (botão "vou pagar até dia X" → libera serviço se policy permitir).

### B5. Central de notificações
- Tela com sino no topo + histórico (manutenção, fatura, OS, promoção).
- Preferências granulares (toggle por categoria).

### B6. Indique e ganhe
- Código único por cliente, share via WhatsApp/link.
- Status: pendente / convertida.
- Recompensa configurável no admin (desconto em fatura).

### B7. Mudança de plano self-service
- Lista de planos disponíveis (admin define visíveis).
- Botão "trocar agora" → gera OS de upgrade/downgrade.

### B8. Chat real-time
- WebSocket (já tem REST), indicador "digitando…", anexar foto.

### B9. Manutenção programada
- Banner no topo da home se houver manutenção na região nas próximas 24h.

### B10. FAQ / base de conhecimento
- Artigos curtos navegáveis antes de abrir OS — reduz volume de ticket.

---

## BLOCO C — Sistema de promoções (dashboard → app) + integração Indicação

**Atualizado 2026-05-21**: Sistema de Indicação F10 já roda (bot WhatsApp + `/admin/indicacoes`). Bloco C **integra** Indicação como tipo especial de promoção, **adicionando o canal "app"** sem quebrar o WhatsApp.

### Execução em 5 fases (C.1 → C.5)

- **C.1** Backend promoções genéricas (tabela, endpoints cliente + admin).
- **C.2** Dashboard `/admin/promocoes` (CRUD, upload imagem, métricas).
- **C.3** App: carrossel real (substitui `home_promos.dart` mockado), eventos view/click.
- **C.4** Integração Indicação: coluna `IndicacaoUso.origem` (`app`|`whatsapp`), endpoint cliente-app `GET /indicacao/meu`, tela Flutter `/indicacao`, banner em `/admin/indicacoes`.
- **C.5** Promoção `tipo: indicacao` ligada à tela `/indicacao` com stats reais.

### Modelo original abaixo

### Modelo de dados
Nova tabela `promocoes`:
```sql
id          uuid pk
titulo      text not null
subtitulo   text
imagem_url  text
cta_label   text
cta_action  text     -- "url:https://...", "tela:/suporte/novo?assunto=upgrade", "info"
ativa       bool default true
ordem       int default 0
valido_de   timestamptz
valido_ate  timestamptz
segmento    text default 'todos'  -- todos | inadimplentes | adimplentes | plano:<id>
created_at, updated_at, created_by
```

Tabela `promocoes_eventos` (analytics):
```sql
id, promocao_id, cliente_id, tipo (view/click), created_at
```

### Dashboard admin
- Rota `/admin/promocoes`: lista (drag-drop reorder), criar, editar, ativar/desativar.
- Upload de imagem (S3 ou bucket local — decidir; default: servir do FastAPI em `/static/promocoes/`).
- Preview "como aparece no app" lado a lado do formulário.
- Filtro por segmento, valido_de/até com date pickers.
- Métricas por promoção: views, clicks, CTR.
- `require_role` admin.

### API
- `GET /api/cliente-app/promocoes` — lista filtrada pelo segmento do cliente logado, ordenada, válidas hoje.
- `POST /api/cliente-app/promocoes/{id}/evento` — body `{tipo: view|click}` (chamado pelo app).
- `GET/POST/PATCH/DELETE /api/admin/promocoes` — CRUD.
- `POST /api/admin/promocoes/{id}/imagem` — upload.

### App Flutter
- Carrossel horizontal swipável na home (entre hero e quick actions).
- Cards com imagem, título, subtítulo, CTA pill.
- Tap registra `click`, scroll que mostra o card registra `view` (debounce).
- Indicadores de página (dots).
- Auto-rotate opcional a cada 5s.
- CTA: abre URL externa OU navega pra tela interna OU é informativo.

---

## BLOCO D — Infra / quality of life (fase final)
- Analytics (eventos: tap, tela, funil onboarding).
- Crashlytics ou Sentry.
- Tema dark polido.
- Acessibilidade (semantics, contraste WCAG AA).
- i18n preparado (PT só por enquanto).
- Loading states consistentes (shimmer).

---

## Princípios de execução
- Trabalho em fases incrementais (estilo Robert).
- Cada fase = commits atômicos + push direto pra `main` (deploy automático via Watchtower).
- CI: respeitar gotchas (ruff/mypy/flutter analyze).
- Não rodar dev stack local — testes acontecem no deploy.
- Cor atual (ciano/marinho) preservada.
