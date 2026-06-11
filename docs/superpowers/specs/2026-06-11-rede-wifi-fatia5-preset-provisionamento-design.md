# Rede WiFi — Fatia 5 (parte 1): Preset de provisionamento no GenieACS

**Data:** 2026-06-11
**Status:** Design aprovado (Robert: "vamos fazer pelo painel"), pronto pra aplicar
**Relacionado:** Fatia 5 (hardening) em `rede-wifi-roadmap`; Fatia 4.1 (selo de saúde depende do sinal popular sozinho)

## Objetivo

Criar um **preset (provision) no GenieACS** que roda a cada Inform de cada ONU e:
1. Liga o **Periodic Inform** (300s) — garante que toda ONU dá inform a cada 5min.
2. Mantém **sinal óptico, aparelhos e PPPoE Username** frescos (relê se >1h) — assim o
   selo de saúde da Fatia 4.1 e a lista de aparelhos populam **sozinhos** pra base inteira,
   sem o técnico/endpoint precisar abrir a tela; e a resolução cliente→ONU por PPPoE esquenta.

**Não** mexe em senha/reboot/config de serviço. **Auth não entra aqui** (fica pra depois do TLS).

## Contexto

- GenieACS self-hosted, painel em `acs.robertbr.dev`. **Provisions/presets vazios** hoje.
- Decisões da Fatia 5 pra rede da Ondeline (CGNAT, sem blocos de IP próprios):
  - Firewall por bloco **descartado** (sem faixas estáveis).
  - STUN **descartado** (CGNAT simétrico quebra STUN; e não precisa de instantâneo — a troca já avisa ~2min).
  - Sobra: **preset → TLS no CWMP (via Nginx Proxy Manager) → auth por ONU**. Esta é a parte 1 (preset).
- Sintaxe `declare()` confirmada na doc oficial (docs.genieacs.com/en/latest/provisions.html):
  - Setar valor: `declare(path, null, {value: X})` (tipo inferido).
  - Freshness: `declare(path, {value: Date.now() - maxAgeMs})` → relê só se mais velho que maxAge.
  - Rediscover de instâncias (wildcard `*`): usar `{path: <timestamp>}`.

## A provision (script do painel)

Nome sugerido: `ondeline-base-preset`. Conteúdo:

```javascript
// Roda a cada Inform. Liga periodic inform e mantem sinal/aparelhos/PPPoE frescos.
// NAO mexe em senha/reboot/config de servico do cliente.
const maxAge = Date.now() - 3600 * 1000;  // "no maximo 1h de idade"

// 1) Periodic Inform: ligado + 300s
declare("InternetGatewayDevice.ManagementServer.PeriodicInformEnable", null, {value: true});
declare("InternetGatewayDevice.ManagementServer.PeriodicInformInterval", null, {value: 300});

// 2) Sinal optico — FiberHome (HG6145D) e Intelbras (AX1800, com o typo de fabrica).
//    GenieACS le so o container que existir no modelo; o outro path da fault por-param
//    (isolado, nao derruba a sessao) -> por isso o rollout valida nos 2 modelos antes da base.
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.RXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.TXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.Status", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.RXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.TXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.Status", {value: maxAge});

// 3) PPPoE Username (warm-up da resolucao cliente->ONU)
declare("InternetGatewayDevice.WANDevice.*.WANConnectionDevice.*.WANPPPConnection.*.Username", {value: maxAge});

// 4) Aparelhos conectados (rediscover instancias + le valores)
declare("InternetGatewayDevice.LANDevice.1.Hosts.Host.*", {path: maxAge, value: maxAge});
```

## O preset (liga a provision aos devices)

- **Channel:** default. **Weight:** 0. **Events:** default (roda no inform/boot/periodic).
- **Configuration:** provision `ondeline-base-preset`.
- **Precondition (rollout em 2 fases):**
  - **Fase A (teste):** só a AX1800 → `{"_deviceId._SerialNumber": "ITBSF191EEB0"}`. Depois um
    HG6145D → `{"_deviceId._ProductClass": "HG6145D"}`. Confirmar que `RXPower`/aparelhos/PPPoE
    populam e que **não há fault de sessão** (faults por-param do container do outro modelo são OK).
  - **Fase B (base toda):** precondition **vazia** (todos os devices).

## Como aplicar (painel `acs.robertbr.dev`)

1. **Admin → Provisions → New**: nome `ondeline-base-preset`, cola o script acima, salva.
2. **Admin → Presets → New**: nome `ondeline-base`, channel default, weight 0, precondition da Fase A
   (serial da AX1800), configuration = a provision. Salva.
3. Espera o próximo inform (~até 5min) e **valida** (probe `/tmp/p.py` ou a tela do técnico):
   `PeriodicInformInterval` virou 300; `RXPower`/aparelhos/PPPoE preenchidos sem ninguém abrir a tela.
   Conferir faults: `GET {nbi}/faults/?query={"device":"<dev>"}` — faults por-param do container do
   outro modelo são esperados/inofensivos; **fault de sessão inteira não pode acontecer**.
4. Repetir num HG6145D (precondition por ProductClass).
5. Se OK nos dois → editar o preset, **apagar a precondition** (vira base toda). Pronto.

## Reversão

Apagar/desabilitar o preset no painel → as ONUs param de receber o provisionamento (o que já foi
setado fica, mas nada novo é forçado). Não há migração nem estado persistente no nosso código.

## Riscos / cuidados

- **Carga:** 300s na base toda aumenta o tráfego de inform — aceitável pra centenas/milhares; monitorar.
- **Fault cross-model:** declarar os 2 containers GPON pode gerar fault por-param no modelo que não tem
  aquele container. GenieACS isola fault por-param; validar no rollout (Fase A) que não vira fault de sessão.
- **Sem auth ainda:** o ACS continua aberto até a parte 2/3 (TLS + auth). Não regride a segurança atual.

## Fora de escopo (próximas partes da Fatia 5)

- **Parte 2:** TLS no CWMP terminado no **Nginx Proxy Manager** (domínio `:443` → `genieacs-cwmp:7547`),
  ONUs com URL `https`.
- **Parte 3:** auth por ONU (credencial no preset, agora sobre TLS; ligar a obrigatoriedade DEPOIS de a
  base ter a credencial).
- Provisionamento da URL do ACS em instalações novas (depende do OLT/OMCI — fato pendente do Robert).
