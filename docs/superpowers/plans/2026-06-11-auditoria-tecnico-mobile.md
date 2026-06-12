# Auditoria do app tecnico-mobile — 2026-06-11

Diagnóstico completo do app Flutter `apps/tecnico-mobile/` (técnico em campo).
Backlog priorizado: bugs confirmados → robustez → segurança → UX → features.

> **Falsos positivos descartados na verificação** (não são bugs, não caçar):
> - `sync_service.dart:180` `return code != null` — lógica está CORRETA (rede pura para o flush; 5xx segue).
> - `reentry_screen.dart` "loop infinito" — não existe; router só redireciona `reentry→os`.
> - `os_detail_screen.dart:323` "setState após dispose" — está guardado por `if (mounted)`.

---

## 🔴 Bugs reais confirmados

- [x] **#1 FCM token marcado antes do registro** — `fcm_service.dart:71-72` ✅ corrigido (jun/2026)
  `_lastToken = token` é setado ANTES do `await post`. Se o registro falha (offline), o token fica
  marcado como registrado e `onTokenRefresh` nunca reenvia. Técnico para de receber push silenciosamente.
  **Fix:** setar `_lastToken` só após sucesso do POST.

- [x] **#2 Listeners FCM nunca cancelados** — `fcm_service.dart:46,49` ✅ corrigido (jun/2026)
  `onTokenRefresh`/`onMessage` sem subscription management. `init()` rodar de novo (logout→login no
  mesmo processo) duplica listeners → notificação exibida 2x.
  **Fix:** guardar as `StreamSubscription` e cancelar em `revoke()`.

- [x] **#3 Ordem delete/markSent na foto** — `sync_service.dart:163-167` ✅ corrigido (jun/2026)
  Deleta o arquivo ANTES de `markSent`. Se o delete falhar, item nunca marca enviado mas o POST já foi
  → reenvio duplicado / arquivo órfão.
  **Fix:** `markSent` primeiro, deletar arquivo depois (best-effort).

- [x] **#4 pppoePass sem trim** — `cliente_novo_screen.dart:231` ✅ corrigido (jun/2026)
  `pppoePass` enviado sem `.trim()` (ao contrário de `pppoeUser`). Espaço acidental → falha de auth PPPoE.
  **Fix:** aplicar mesma normalização do user.

---

## 🟠 Robustez / offline

- [x] **Sync silencioso em DB travado** — `sync_service.dart:108` `flush()` não loga quando `pending()` lança. ✅ corrigido: `catch` com `developer.log` (jun/2026)
- [x] **Badge pending desatualizado 5s** — `pendingCountProvider` faz polling 5s. ✅ corrigido: agora usa `watchPendingCount()` (stream reativo do Drift, atualiza no instante do enqueue/markSent) (jun/2026)
- [x] **Migration v4 destrutiva** — `database.dart` `deleteTable('estoque_local')` sem transação. ✅ corrigido: drop+create dentro de `transaction()` (jun/2026)
- [x] **Defaults silenciosos** — `cliente_cadastro_repo.dart` `normalize…` injeta `id:''`, `dob:'1900-01-01'` quando API omite campos. ✅ corrigido: `replaceAll`/`upsertOne` pulam e logam quando `id` está vazio (não cacheia órfão) (jun/2026)
- [~] **Sem índices Drift** — **analisado e descartado**: queries por `userId` já são cobertas pelos composite PKs `{userId,id}`/`{userId,itemId}` (SQLite indexa o PK e `userId` é a coluna mais à esquerda). Índice em `syncedAt` teria ganho marginal (dataset por-técnico é pequeno) e exigiria bump de schema + `build_runner` (codegen do `database.g.dart`) que não roda no ambiente local. Reavaliar só se surgir lentidão real em campo.

## 🟡 Segurança / produção

- [x] **`/design-preview` sempre registrada** — `router.dart:25,53` sem auth. Risco baixo em mobile, mas dead code de dev em release. **Fix:** `if (kDebugMode && loc == '/design-preview')` + registrar rota só em debug. ✅ corrigido (jun/2026)
- [ ] **Logout não faz deleteAll** — `auth_storage` limpa chaves individuais; `deleteAll()` em `clearAuth()` é mais robusto.
- [ ] **Dead code branding** — `brand_tokens.dart` `BrandTokens.light` morto convive com `lightCorrected` (o usado). Remover o morto.

## 🟡 UX

- [ ] **Botão "Iniciar visita" sem loading** — `os_detail` não desabilita durante captura GPS (até 8s). Técnico clica de novo.
- [ ] **Erros genéricos** — `rede_screen` ("Falha ao trocar a senha"), `os_detail` (`_actionFailureMessage`), `perfil` avatar. Engolem motivo real (offline, serial inválido, 403).
- [ ] **Avatar perfil** — tap target ~26px (<44px) e sem `Semantics`.
- [ ] **CEP cadastro** — falha de rede e "CEP não encontrado" mesma mensagem; sem ✓ de sucesso. UF é TextField livre → dropdown dos 27 estados.
- [ ] **Busca estoque sem debounce** — `setState` por tecla (ok hoje, escala mal).

## 🟢 Features novas

Alto valor:
- [ ] **#F1 Validar GPS de conclusão** — comparar `gps_fim` com endereço da OS (alertar se >500m). Anti-fraude.
- [ ] **#F2 Material da OS decrementa estoque** — hoje texto livre, não baixa saldo. Reusar picker do cadastro.
- [ ] **#F3 Scanner código de barras/QR no estoque** — `mobile_scanner`.
- [ ] **#F4 Rascunho local do cadastro** — salvar steps em Drift, oferecer "continuar cadastro".
- [ ] **#F5 Resumo antes de enviar** (step 3) — read-only confirmando dados antes do POST.

Médio valor:
- [ ] **#F6 Paginação** nas listas OS/clientes (hoje renderiza tudo).
- [ ] **#F7 CSAT com comentário** — se nota <3, perguntar motivo.
- [ ] **#F8 Preview da foto antes de enfileirar** (OS e cadastro).
- [ ] **#F9 Cache dos planos SGP** (24h) — offline + velocidade.
- [ ] **#F10 Persistir tema light/dark** — verificar se o seletor grava a escolha.

---

## Ordem de execução acordada

1. Bugs confirmados (#1 FCM, #4 pppoePass, design-preview) — leva rápida
2. #2 listeners FCM, #3 ordem foto
3. Features #F1 (GPS conclusão) e #F2 (decremento estoque) — maior impacto
4. Demais conforme prioridade

> Sem stack local: testes acontecem na máquina de deploy após push. Não commitar/pushar sem OK.
