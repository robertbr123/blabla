# Templates WhatsApp Cloud API — Variante "Abrir no app"

> Versão alternativa dos templates do **cliente** com chamada pra abrir o
> cliente-mobile. O doc original [`whatsapp-cloud-templates.md`](./whatsapp-cloud-templates.md)
> continua sendo a referência "normal" (só Quick reply). Use **um ou outro** —
> não os dois pro mesmo template no Meta.

**Padrão usado aqui (Opção B — híbrido):**
- Link `clientes.ondeline.com.br/<path>` **no corpo do texto** → abre direto no
  app via App Link. Se o app não estiver instalado, cai na landing com botões
  pra Play/App Store.
- **Mantém os Quick reply** existentes. O Meta **não deixa misturar** Quick
  reply + botão URL no mesmo template, então o link vai no corpo (não como botão).

**Paths suportados pelo App Link do cliente-mobile (v1):**

| Path | Abre |
|------|------|
| `clientes.ondeline.com.br/faturas` | aba Faturas |
| `clientes.ondeline.com.br/suporte` | aba Suporte |
| `clientes.ondeline.com.br/notificacoes` | tela de Notificações |

> ⚠️ Qualquer mudança de body = **re-submeter o template no Meta** e esperar
> re-aprovação (geralmente <1h). Idioma `pt_BR`, categoria UTILITY.

> ℹ️ Os templates do **técnico** (`os_atribuida_tecnico`) e de **autenticação**
> (`otp_login_cliente_app`) não mudam — ficam como no doc original.

---

## 1. `fatura_vencendo`

**Body:**
```
Olá, {{1}} 👋

Sua fatura *vence em {{2}}*
Valor: *R$ {{3}}*

Posso te mandar o boleto e o PIX aqui mesmo 👇
Ou, se preferir, é só abrir no app:
clientes.ondeline.com.br/faturas
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:**
- Quick reply: `Quero o boleto`
- Quick reply: `Já paguei`

---

## 2. `fatura_vencida`

**Body:**
```
Olá, {{1}} 👋

Notamos que sua fatura está com *{{2}} dia(s) de atraso*.

Vamos regularizar juntos? Posso te enviar aqui:
   ▸ Boleto atualizado
   ▸ PIX copia-e-cola

Ou acompanhe tudo no app: clientes.ondeline.com.br/faturas
```

**Footer:** `Ondeline · Atendimento automático`

**Botões:**
- Quick reply: `Enviar boleto`
- Quick reply: `Falar com humano`

---

## 3. `os_concluida_csat`

**Body:**
```
Olá, {{1}} 👋

Sua ordem de serviço foi *concluída*.

   ▸ OS: {{2}}
   ▸ Atendimento: {{3}}

Ficou tudo certo? Avalie em segundos pelo app:
clientes.ondeline.com.br/suporte
```

**Footer:** `Responda de 1 a 5 ⭐`

**Botões:**
- Quick reply: `Ficou ótimo`
- Quick reply: `Ainda tem problema`

---

## 4. `manutencao_programada`

**Body:**
```
Olá, {{1}} 🛠

*Manutenção programada na sua região*

   ▸ {{2}}
   ▸ Janela: {{3}}

Sua conexão pode oscilar nesse período.
Detalhes e avisos no app: clientes.ondeline.com.br/notificacoes
```

**Footer:** `Ondeline · Aviso operacional`

**Botões:** nenhum.

---

## 5. Régua de cobrança — 4 templates

Mesmos parâmetros nos 4: `{{1}}` nome, `{{2}}` valor, `{{3}}` data vencimento.
Link do app no corpo aponta pra `/faturas`.

### 5a. `cobranca_regua_dia0`
```
Oi, {{1}}

Sua fatura *venceu hoje* ({{3}}).
Valor: *R$ {{2}}*

Posso resolver agora pra você em 1 minuto.
Ou abra no app: clientes.ondeline.com.br/faturas
```

### 5b. `cobranca_regua_dia3`
```
Oi, {{1}}

Sua fatura de *R$ {{2}}* está com *3 dias de atraso* (venceu em {{3}}).

Vamos regularizar? Eu te mando boleto atualizado e PIX.
Ou abra no app: clientes.ondeline.com.br/faturas
```

### 5c. `cobranca_regua_dia7`
```
Oi, {{1}}

Sua fatura de *R$ {{2}}* completa *7 dias de atraso* hoje
(vencimento original: {{3}}).

Pra evitar bloqueio, dá pra acertar agora?
Ou abra no app: clientes.ondeline.com.br/faturas
```

### 5d. `cobranca_regua_dia15`
```
{{1}}, precisamos da sua atenção

Fatura em aberto há *15 dias*
   ▸ Valor: R$ {{2}}
   ▸ Vencimento: {{3}}

Pra manter seu plano ativo, regularize agora.
Tudo no app: clientes.ondeline.com.br/faturas
```

**Footer (todos os 4):** `Ondeline · Cobrança automática`

**Botões (todos os 4):**
- Quick reply: `Quero o boleto`
- Quick reply: `Pagar via PIX`
- Quick reply: `Falar com humano`
