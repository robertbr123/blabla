# Onda 10 — Telefone desatualizado no SGP: caminho de atualização via WhatsApp

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Cliente com número desatualizado/ausente no SGP ganha caminho seguro: na tela do OTP, "Não usa mais esse número?" abre o WhatsApp da Ondeline com mensagem pré-preenchida (com CPF) pro atendente atualizar o cadastro; e o caso "cadastro sem telefone" (hoje um 409 ambíguo) vira fluxo próprio com o mesmo CTA. NUNCA troca automática de número sem verificação humana (segurança: anti account-takeover).

## Global Constraints

- `apps/api` (T1) + `apps/cliente-mobile` (T1, T2). Commits direto na main, um por task. NÃO push.
- Gate Flutter: `flutter test` verde (23) + `flutter analyze lib test` grepado `error •|warning •` = zero (~124 infos, não crescer). Gate API: ruff limpo; pytest → CI.
- Compat: app antigo + API nova não pode quebrar (o detail dict cai no fallback por statusCode do _messageFromDio antigo — aceitável).

---

### Task 1: caso "sem telefone no SGP" tipado (API + app)

**Files:** `apps/api/src/ondeline_api/api/v1/cliente_app_auth.py`, teste da API, `apps/cliente-mobile/lib/core/auth/auth_repository.dart` (+ onde os Results moram), `apps/cliente-mobile/lib/features/onboarding/onboarding_cpf_screen.dart`

- [ ] **API:** no `register/start`, o raise atual `HTTPException(409, detail="cliente sem telefone cadastrado no SGP")` passa a `detail={"code": "sem_telefone", "msg": "cliente sem telefone cadastrado no SGP"}` (mantém 409). O caso "usuario ja cadastrado" fica INTACTO. Teste cobrindo o shape novo.
- [ ] **App:** `registerStart` — no catch, se `statusCode == 409` e o detail for Map com `code == 'sem_telefone'` → novo caso `RegisterStartSemTelefone` (no estilo dos outros); 409 restante continua `alreadyExists`.
- [ ] **App:** `onboarding_cpf_screen` — caso `SemTelefone` abre sheet (padrão dos existentes): ícone `Icons.phone_disabled_rounded` 48 warning; título `Achamos seu cadastro, mas...`; corpo `Ele está sem um WhatsApp válido. Fala com a gente que atualizamos rapidinho — aí é só voltar e continuar.`; botão verde WhatsApp `Atualizar meu cadastro` → helper de WhatsApp com mensagem `Olá! Quero atualizar o telefone do meu cadastro pra acessar o app. Meu CPF é {cpf formatado}.` (usar o CPF digitado); TextButton `Fechar`.
- [ ] Gates + commit único: `feat(api+cliente): caso sem telefone no SGP tipado com CTA de atualizacao via whatsapp`.

### Task 2: helper compartilhado + "Não usa mais esse número?" no OTP

**Files:** `apps/cliente-mobile/lib/core/ui/whatsapp_comercial.dart` (novo), `apps/cliente-mobile/lib/features/onboarding/onboarding_cpf_screen.dart` (refactor), `apps/cliente-mobile/lib/features/onboarding/onboarding_otp_screen.dart`

- [ ] **Extrair helper:** `Future<bool> abrirWhatsappComercial(WidgetRef ref, {required String mensagem})` pra `lib/core/ui/whatsapp_comercial.dart` — mesma lógica do `_abrirWhatsappComercial` atual (contatosOperadoraProvider best-effort, tipo 'whatsapp', wa.me com texto encoded, launchUrl com retorno respeitado). O cpf_screen passa a usá-lo (mensagem atual mantida lá).
- [ ] **OTP screen:** abaixo do reenviar código, adicionar: `Não usa mais esse número?` (12, textSecondary) + TextButton `Atualizar meu cadastro pelo WhatsApp` (foreground `BrandTokens.brandWhatsapp`, w700) → helper com a mensagem `Olá! Quero atualizar o telefone do meu cadastro pra acessar o app. Meu CPF é {cpf formatado}.` (o OTP screen recebe o cpf — conferir). Falha → toast `Não conseguimos abrir o WhatsApp agora. Tenta de novo mais tarde.` Lógica do OTP intacta.
- [ ] Gates + commit: `feat(cliente): atualizar telefone via whatsapp na tela do codigo`.

### Task 3: verificação

- [ ] Gates + `flutter build apk --debug`. Review whole-branch (base = commit anterior à T1): compat do detail dict, fluxos 404/409/sem_telefone/ok, helper único sem duplicação.
- [ ] Checklist manual (Robert): CPF sem telefone → sheet novo; OTP → link de atualizar abre WhatsApp com CPF na mensagem. Precisa de deploy da API pro caso sem_telefone tipado.
