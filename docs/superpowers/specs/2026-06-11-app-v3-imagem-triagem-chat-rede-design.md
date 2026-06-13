# App v3 — Imagem na landing de promo, Triagem pré-chamado, Chat com rede (GenieACS)

**Data:** 2026-06-11
**Status:** Design aprovado em conversa com Robert.

## Contexto

Três melhorias no app cliente, decididas via brainstorming:
1. Landing de promoção deve mostrar a **imagem** da promo em destaque (hoje só gradiente + ícone).
2. Antes de abrir chamado "Sem internet", rodar uma **varredura diagnóstica** (GenieACS: dispositivos + sinal), mostrar ao cliente e só então liberar a abertura — com o diagnóstico anexado.
3. O **chat in-app** deve consultar a rede do cliente como o bot do WhatsApp já faz (tool `consultar_rede`), aproveitando que o user do app já é autenticado (CPF do token, sem fluxo de identificação).

## Decisões do brainstorming

1. **Imagem da landing**: usar a MESMA `imagem_url` que já existe (upload atual da dashboard), exibida nítida; ícone vira fallback. Sem campo novo.
2. **Triagem**: só pro tipo `sem_internet` (mudança de endereço e troca de plano vão direto pro form).
3. **Diagnóstico**: anexado ao chamado (`payload_json.diagnostico`) — atendente abre o chamado já sabendo o estado da rede.
4. **Chat**: escopo v1 = só `consultar_rede` (abrir chamado pelo chat fica pra v2). Arquitetura B: mini-loop de tools no próprio endpoint do chat (não reusa o pipeline do WhatsApp — sem acoplamento com Conversa/Evolution).

## Design

### Fatia 1 — Imagem em destaque na landing (só app Flutter)

`lib/features/promocoes/promocao_detalhe_screen.dart`:
- Promo COM `imagem_url`: o background do SliverAppBar mostra a imagem nítida (`BoxFit.cover`, sem opacity reduzida), com gradiente escuro sutil na base (scrim) pra legibilidade do título colapsado. SEM ícone central.
- Promo SEM imagem: visual atual (gradiente from/to + ícone central). 
- Card do carrossel/lista NÃO muda (continua imagem a 35% atrás do gradiente).
- Zero mudança em API/dashboard.

### Fatia 2 — Triagem "varredura" no chamado Sem Internet (só app Flutter)

Fluxo no wizard de novo chamado (`novo_chamado_screen.dart`), apenas quando tipo = `sem_internet`:

1. **Tela de varredura**: animação de scan (radar/pulso com identidade visual da marca) enquanto chama em paralelo `GET /cliente-app/rede/status` e `GET /cliente-app/rede/aparelhos` (endpoints existentes, contrato-aware).
2. **Resultado** (cards): ONU online/offline · X dispositivos conectados (lista expansível com nomes) · selo do sinal (excelente/boa/fraca) com explicação leiga.
3. **Orientação por cenário**:
   - Tudo excelente → "tua conexão parece saudável; reiniciar o roteador resolve na maioria dos casos".
   - Muitos dispositivos (>= 10) → dica de congestionamento.
   - Sinal fraco ou ONU offline → "identificamos um problema do nosso lado" (mensagem específica).
4. **Decisão**: botão "Resolveu, valeu!" (encerra) ou "Ainda preciso de ajuda" → formulário normal.
5. **Anexo**: resultado vai em `payload_json.diagnostico` do `POST /cliente-app/os` — `{online, total_aparelhos, saude, timestamp}` (sem rx_power cru: os endpoints cliente-app expõem só o selo `saude`, derivado do rx no backend). `payload_json` já é dict livre → **sem migration**. Dashboard de OS (`/cliente-app-os`) mostra bloco "Diagnóstico na abertura" quando presente.
6. **Bypass**: `encontrada: false` (sem ONU mapeada), erro ou timeout (12s) → pula direto pro formulário com aviso discreto. Triagem nunca bloqueia chamado.

### Fatia 3 — Chat in-app com consultar_rede (API)

`apps/api/src/ondeline_api/api/v1/cliente_app_chat.py` (`/send`):
- Mini-loop de function-calling (máx 3 iterações) no HermesProvider (que já suporta tools no pipeline do WhatsApp).
- Tool única `consultar_rede_app`: resolve CPF do user autenticado (decrypt) e chama `RedeService.diagnostico_rede(cpf, contrato_id)` — mesmo serviço usado pelo WhatsApp e pela tela Minha Rede. Não reusa `ToolContext`/registry do WhatsApp (evita acoplamento com Conversa/Evolution).
- System prompt atualizado: bot PODE consultar dispositivos/sinal do cliente; usar quando reclamarem de lentidão/queda; traduzir resultado pra leigo; sinal fraco/offline → orientar abrir chamado pelo botão de Novo Chamado (tool de abrir chamado é v2).
- Guard-rails: tool read-only; handoff humano inalterado (bot não responde com atendente ativo); erro GenieACS → bot diz que não conseguiu consultar agora (turno não quebra).
- Latência +2-4s aceitável (polling 5s, UI mostra "digitando"). Tokens contabilizados em `llm_tokens_used` como hoje.

## Erros e testes

- Triagem: timeout 12s → bypass; chamadas paralelas com `Future.wait` tolerante a falha individual.
- API: testes do tool-loop do chat (mock RedeService) + teste do `payload_json.diagnostico` persistido no POST /os.
- Flutter: analyze + test; smoke manual no device.
- Entrega: 3 fatias independentes, ordem 1 → 2 → 3.
