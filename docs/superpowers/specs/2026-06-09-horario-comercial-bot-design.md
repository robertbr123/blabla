# Horário comercial no bot — Design

**Data:** 2026-06-09
**Status:** Aprovado (aguardando implementação)

## Problema

O bot responde 24/7 e, ao escalar para humano, **promete atendimento imediato** mesmo
fora do expediente ("em instantes um atendente vai falar com você"). Isso gera
frustração e reclamação quando ninguém responde até o dia seguinte.

## Escopo (decidido)

- **Comportamento:** o bot continua respondendo/resolvendo 24/7. Muda **apenas a
  mensagem de hand-off**: fora do expediente, em vez de prometer humano imediato,
  informa a janela de atendimento e que um atendente retorna no próximo horário comercial.
- **Janela:** Seg–Sex, janela única, configurável por env. Sábado/domingo = fechado.
- **Fora de escopo (YAGNI):** sábado, feriados, config por canal, silenciar o bot,
  bloquear escalonamento, e cálculo dinâmico de "retornamos amanhã às X" (usa janela fixa).

## Config (Settings / env)

| Var | Default | Descrição |
|-----|---------|-----------|
| `business_hours_enabled` | `False` | Liga/desliga o gating. **Default OFF** — o deploy não muda comportamento; liga em prod via `.env` após confirmar o horário real. |
| `business_hours_start` | `"08:00"` | Início da janela (HH:MM) |
| `business_hours_end` | `"18:00"` | Fim da janela (HH:MM) |
| `business_days` | `"1,2,3,4,5"` | Dias úteis (ISO: Seg=1 … Dom=7) |

Timezone fixo `America/Sao_Paulo` (já é o padrão do projeto).

## Componente novo: `services/business_hours.py`

Módulo isolado e testável, sem dependência de DB/rede.

- `is_open(now: datetime | None = None) -> bool`
  - Se `business_hours_enabled` for `False` → sempre `True` (mantém comportamento atual).
  - Converte `now` (UTC, default `datetime.now(tz=UTC)`) para `America/Sao_Paulo`.
  - Retorna `True` se o dia ∈ `business_days` **e** `start <= hora < end`.
- `closed_notice() -> str`
  - Frase fixa de expectativa, ex.:
    *"Nosso atendimento humano é de segunda a sexta, das 8h às 18h. Já registrei sua
    mensagem e um atendente retorna no próximo horário comercial. 🕐"*
  - Deriva a frase do `start`/`end`/`business_days` configurados (não hardcoda 8h–18h).

## Pontos de integração (só alteram quando FECHADO)

Helper central: `business_hours.humano_message(open_msg, closed_prefix="")` — devolve
`open_msg` dentro do expediente; fora, `closed_prefix + closed_notice()`.

**Mensagens determinísticas de hand-off** (a maioria é hardcoded, NÃO gerada pelo LLM):

1. **Aviso pós-`transferir_para_humano`** — `services/llm_loop.py:~465`. **Principal caminho:**
   o LLM chama a tool e o código envia um `aviso` fixo. → `humano_message`.
2. **`_force_escalate`** — `services/llm_loop.py:~494` (max_iter/erro/orçamento). → `humano_message`.
3. **Acks de mídia que escalam** — `services/media_classifier.py:CATEGORY_ACK` (escalate) +
   `services/inbound.py` (`CATEGORIES_ESCALATE`): acks reescritos sem promessa de tempo +
   `handoff_phrase()` no envio.
4. **Boas-vindas de indicação** — `services/inbound.py:~996`: variante fechado.
5. **Mudança de endereço + pendência** — `services/inbound.py:~1440`. → `humano_message`.
6. **Followup de OS não resolvida** — `workers/followup.py` (`_MSG_ESCALAR`). → `humano_message`.
7. **Ack genérico legado** — `InboundDeps.ack_text` (`SEND_ACK`, dormente). → hours-aware.

**Caminho do LLM (secundário)** — `services/llm_loop.py` `run_turn`: quando fechado, injeta
`llm_prompt_hint()` no contexto dinâmico, cobrindo o caso raro em que o LLM escreve o próprio
texto de transferência em vez de usar o `aviso` padrão.

## Tratamento de erro

- `is_open` é puro e não lança (parsing de config validado no boot). Em caso de config
  inválida, log de warning + fail-open (`True`, comportamento atual) para não silenciar o bot.

## Testes

`apps/api/tests/test_business_hours.py`:
- `is_open` dentro da janela (dia útil, meio do horário) → `True`
- fora da janela (dia útil, antes/depois) → `False`
- fim de semana → `False`
- bordas (exatamente `start` → aberto; exatamente `end` → fechado)
- fuso correto (um horário UTC que cai dentro/fora ao converter pra SP)
- `business_hours_enabled=False` → sempre `True`
- `closed_notice()` reflete a janela configurada

Observação: testes rodam no CI / máquina de deploy (sem stack local).

## Critério de pronto

- Fora do expediente, todos os pontos de hand-off (acks determinísticos + texto do LLM)
  informam a janela e o retorno no próximo horário comercial, sem prometer humano imediato.
- Dentro do expediente, comportamento idêntico ao atual.
- `business_hours_enabled=False` reproduz exatamente o comportamento atual.
