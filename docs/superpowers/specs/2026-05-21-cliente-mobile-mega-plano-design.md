# Cliente Mobile — Mega Plano de Evolução

**Data:** 2026-05-21
**App alvo:** `apps/cliente-mobile` (Flutter)
**Stack:** Flutter 3.27+ · Riverpod · go_router · Dio · FastAPI backend · Next.js dashboard
**Objetivo:** Transformar o app cliente atual num app de provedor de internet completo, moderno, com sistema de promoções gerenciável pelo dashboard.

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

## BLOCO C — Sistema de promoções (dashboard → app)

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
