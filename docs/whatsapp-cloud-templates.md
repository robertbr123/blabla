# Templates WhatsApp Cloud API — Meta Business

Os 9 templates necessários pra integração com WhatsApp Cloud API (Meta).
Cole o conteúdo abaixo em business.facebook.com → WhatsApp Manager → tua WABA → **Modelos de mensagem** → **Criar modelo**.

**Idioma:** todos em `pt_BR`.
**Categoria:** UTILITY (transacional), exceto `otp_login_cliente_app` que é AUTHENTICATION.

Os nomes dos templates batem com o registry em `apps/api/src/ondeline_api/services/whatsapp_templates.py` — se renomear no Meta, atualizar lá também.

## ✏️ Convenção de voz (saudações)

Pra a marca ficar consistente entre templates:

| Contexto | Abertura | Onde |
|----------|----------|------|
| **Utilitário / serviço** (faturas, OS, manutenção, boleto) | `Olá, {{1}} 👋` (ou emoji contextual: ✅ 📄 🛠) | mensagens informativas/positivas |
| **Cobrança** (régua dia 0/3/7) | `Oi, {{1}}` | tom mais próximo, conversacional |
| **Alerta sério** (dia 15 em diante) | `{{1}}, precisamos da sua atenção` | sem saudação — peso |
| **Autenticação** | n/a | formato fixo do Meta, não mexer |

Emoji acompanha a saudação **só uma vez** por mensagem; o resto do corpo usa emoji só quando agrega (▸ ✅ 📄 🛠).

---

## 🌐 Hosts em uso (estado atual e migração futura)

| App | Host atual | Host alvo (futuro) |
|-----|-----------|--------------------|
| **tecnico-pwa** | `https://tec.robertbr.dev` ✅ | `https://tecnico.ondeline.com.br` (planejado) |
| **cliente-pwa** (se houver) | — | a definir |

### TODO — quando migrar o tecnico pro domínio definitivo

Lista pra você executar quando trocar de host (ex: `tec.robertbr.dev` → `tecnico.ondeline.com.br`):

1. **DNS + deploy do tecnico-pwa** no novo domínio (com HTTPS válido).
2. **Template `os_atribuida_tecnico` no Meta Business Manager** → editar a URL do botão (de `tec.robertbr.dev/os/{{1}}` pra `<novo>/os/{{1}}`) → **re-aprovação** automática (geralmente <1h).
3. **`apps/tecnico-mobile/android/app/src/main/AndroidManifest.xml`** → trocar `android:host` no `intent-filter` de App Links.
4. **`apps/tecnico-mobile/ios/Runner.entitlements`** → trocar `applinks:<host>` (e re-adicionar no Xcode "Associated Domains" se preferir).
5. **`apps/tecnico-pwa/public/.well-known/`** → os arquivos `assetlinks.json` e `apple-app-site-association` continuam iguais; só precisam estar **acessíveis no host novo** (deploy faz isso).
6. **`apps/api/src/ondeline_api/services/whatsapp_templates.py`** → se algum template usar o host hardcoded (hoje não usa, mas conferir).
7. **Build novo de Android + iOS** e publicar nas lojas pra app verificar o novo host (`autoVerify` re-roda na primeira instalação/atualização).
8. **Validação pós-migração:**
   ```bash
   curl -I https://<novo>/.well-known/assetlinks.json
   curl -I https://<novo>/.well-known/apple-app-site-association
   adb shell pm verify-app-links --re-verify br.com.linket.blabla
   ```

Manter o `tec.robertbr.dev` no ar por uns dias depois da migração (redirect 301 → novo host) pra absorver links antigos que ainda circularem.

---

## 1. `fatura_vencendo`

- **Nome:** `fatura_vencendo`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
Olá, {{1}} 👋

Sua fatura *vence em {{2}}*
Valor: *R$ {{3}}*

Posso te enviar o boleto e o PIX agora mesmo?
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:**
- Quick reply: `Quero o boleto`
- Quick reply: `Já paguei`

**Exemplos de variáveis:**
- `{{1}}` → `João`
- `{{2}}` → `05/12/2026`
- `{{3}}` → `99,90`

---

## 2. `fatura_vencida`

- **Nome:** `fatura_vencida`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
Olá, {{1}} 👋

Notamos que sua fatura está com *{{2}} dia(s) de atraso*.

Vamos regularizar juntos? Em segundos eu te envio:
   ▸ Boleto atualizado
   ▸ PIX copia-e-cola
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:**
- Quick reply: `Enviar boleto`
- Quick reply: `Falar com humano`

**Exemplos de variáveis:**
- `{{1}}` → `João`
- `{{2}}` → `3`

---

## 3. `pagamento_confirmado`

- **Nome:** `pagamento_confirmado`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
Olá, {{1}} ✅

Pagamento *confirmado* com sucesso.

Obrigado pela parceria 🙌
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:** nenhum (mensagem de fechamento).

**Exemplos de variáveis:**
- `{{1}}` → `João`

---

## 4. `os_concluida_csat`

- **Nome:** `os_concluida_csat`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
Olá, {{1}} 👋

Sua ordem de serviço foi *concluída*.

   ▸ OS: {{2}}
   ▸ Atendimento: {{3}}

Ficou tudo certo? Sua avaliação ajuda a gente a melhorar.
```

**Footer:** `Responda de 1 a 5 ⭐`

**Botões:**
- Quick reply: `Ficou ótimo`
- Quick reply: `Ainda tem problema`

**Exemplos de variáveis:**
- `{{1}}` → `João`
- `{{2}}` → `OS-12345`
- `{{3}}` → `Sem sinal de internet`

---

## 5. `manutencao_programada`

- **Nome:** `manutencao_programada`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
Olá, {{1}} 🛠

*Manutenção programada na sua região*

   ▸ {{2}}
   ▸ Janela: {{3}}

Sua conexão pode oscilar nesse período.
Obrigado pela compreensão.
```

**Footer:** `Ondeline · Aviso operacional`

**Botões:** nenhum.

**Exemplos de variáveis:**
- `{{1}}` → `João`
- `{{2}}` → `Troca de fibra na região central`
- `{{3}}` → `14:00-16:00`

---

## 6. Régua de cobrança — 4 templates

Crie os 4 separadamente. Mesmos parâmetros nos 4: `{{1}}` nome, `{{2}}` valor, `{{3}}` data vencimento.

### 6a. `cobranca_regua_dia0`

- **Categoria:** UTILITY · **Idioma:** `pt_BR`

**Body:**
```
Oi, {{1}}

Sua fatura *venceu hoje* ({{3}}).
Valor: *R$ {{2}}*

Posso resolver agora pra você em 1 minuto.
```

### 6b. `cobranca_regua_dia3`

**Body:**
```
Oi, {{1}}

Sua fatura de *R$ {{2}}* está com *3 dias de atraso* (venceu em {{3}}).

Vamos regularizar? Eu te mando boleto atualizado e PIX.
```

### 6c. `cobranca_regua_dia7`

**Body:**
```
Oi, {{1}}

Sua fatura de *R$ {{2}}* completa *7 dias de atraso* hoje
(vencimento original: {{3}}).

Pra evitar bloqueio, dá pra acertar agora?
```

### 6d. `cobranca_regua_dia15`

**Body:**
```
{{1}}, precisamos da sua atenção

Fatura em aberto há *15 dias*
   ▸ Valor: R$ {{2}}
   ▸ Vencimento: {{3}}

Pra manter seu plano ativo, posso te enviar agora condições especiais de regularização.
```

**Footer (todos os 4):** `Ondeline · Cobrança automática`

**Botões (todos os 4):**
- Quick reply: `Quero o boleto`
- Quick reply: `Pagar via PIX`
- Quick reply: `Falar com humano`

**Exemplos de variáveis (todos):**
- `{{1}}` → `João`
- `{{2}}` → `99,90`
- `{{3}}` → `25/05/2026`

---

## 7. `boleto_com_pdf`

- **Nome:** `boleto_com_pdf`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Header:** tipo **DOCUMENT** (Meta vai pedir um PDF de exemplo na submissão — pode usar um boleto mockado qualquer).

**Body:**
```
Olá, {{1}} 📄

Segue seu *boleto em anexo*.

   ▸ Vencimento: {{2}}
   ▸ Valor: *R$ {{3}}*

Qualquer dúvida, estou por aqui.
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:** nenhum.

**Exemplos de variáveis:**
- `{{1}}` → `João`
- `{{2}}` → `05/12/2026`
- `{{3}}` → `99,90`

> ⚠️ Pra enviar PDF gerado on-the-fly (boleto da régua), precisa um patch no `CloudAdapter.send_template` pra fazer upload + media_id antes. Não está incluído no PR4.

---

## 8. `otp_login_cliente_app` (AUTHENTICATION)

- **Nome:** `otp_login_cliente_app`
- **Categoria:** **AUTHENTICATION** (formato rígido — Meta gera o body)
- **Idioma:** `pt_BR`

**Tipo:** `One-time password`

**Body (gerado pelo Meta — você só confirma):**
```
*{{1}}* é seu código de verificação.
Por segurança, não compartilhe este código com ninguém.
```

**Botão (auto):** `Copiar código`

**Validade do código:** 10 minutos

**Exemplos de variáveis:**
- `{{1}}` → `123456`

> 💡 AUTHENTICATION aprova em minutos e é mais barato que UTILITY.

---

## 9. `os_atribuida_tecnico`

- **Nome:** `os_atribuida_tecnico`
- **Categoria:** UTILITY
- **Idioma:** `pt_BR`

**Body:**
```
🛠 *Nova OS atribuída a você*

   ▸ OS: {{1}}
   ▸ Cliente: {{2}}
   ▸ Endereço: {{3}}
   ▸ Problema: {{4}}

Abra o app pra iniciar o atendimento.
```

**Footer:** `Ondeline · Operacional`

**Botão:**
- URL: `Abrir OS no app` → `https://tec.robertbr.dev/os/{{1}}`
  (placeholder dinâmico — Meta vai pedir um exemplo de URL completa)

> 🔗 **App Links / Universal Links ativos:** essa URL abre direto no
> **tecnico-mobile** quando o app estiver instalado (Android via intent-filter
> `autoVerify` + `/.well-known/assetlinks.json` em `tec.robertbr.dev`; iOS via
> `applinks:tec.robertbr.dev` + `/.well-known/apple-app-site-association`).
> Se o app **não** estiver instalado, cai automaticamente no `tecnico-pwa` —
> o template **não muda**.
> Após publicar na Play com Play App Signing, **adicionar o SHA256 da chave
> de app signing** do Console em `assetlinks.json` (aceita array de fingerprints).

**Exemplos de variáveis:**
- `{{1}}` → `OS-12345`
- `{{2}}` → `João da Silva`
- `{{3}}` → `Rua das Flores, 123 - Centro`
- `{{4}}` → `Sem sinal de internet`

---

## Regras gerais do Meta (não esquecer)

1. **Idioma exato:** `pt_BR` (underscore, BR maiúsculo). Não `pt-BR` nem `pt`.
2. **Toda variável precisa exemplo realista** — Meta rejeita "teste"/"lorem ipsum".
3. **Variáveis em sequência sem texto entre** (`{{1}}{{2}}`) é rejeitado. Sempre tem que ter palavra/separador entre placeholders.
4. **Sem gatilhos promocionais em UTILITY:** evite "promoção", "desconto", "oferta", "exclusivo", "grátis". Rebaixam pra MARKETING (mais caro, formato diferente).
5. **Emojis funcionais OK** (✅ 📄 🛠 👋 ⭐). Evite os "exagerados" (🎉 🔥 💰 💎) que disparam reclassificação.
6. **Aprovação:** UTILITY/AUTH bem formatados aprovam em <1h geralmente. Pior caso: 24h.

## Setup do webhook no Meta (depois dos templates)

1. business.facebook.com → WhatsApp Manager → Configuration → Webhooks
2. **Callback URL:** `https://SEU-DOMINIO/webhook/whatsapp-cloud`
3. **Verify token:** gere com `openssl rand -hex 32` — cole aqui E em `WHATSAPP_CLOUD_VERIFY_TOKEN` no `.env` da VPS
4. **Subscribe to:** marcar `messages`
5. **App Secret** (Settings → Basic) → `WHATSAPP_CLOUD_APP_SECRET` no `.env`
6. **Access token** (System User permanente) → `WHATSAPP_CLOUD_ACCESS_TOKEN` no `.env`

Reiniciar API: `docker restart blabla-api`
