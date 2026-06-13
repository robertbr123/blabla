# GenieACS — Preset de frescor (sinal / PPPoE / aparelhos)

**Status: NÃO aplicado ainda.** Rascunho pronto pra colar no GenieACS quando for
ligar a base real (faz parte da Fatia 5 — hardening / provisionar a base).
Hoje a coleta funciona on-demand (o backend dispara `refresh_wan` quando alguém
abre o diagnóstico). Este preset troca o on-demand por "fresco a cada inform"
pro parque inteiro, sem precisar abrir cada ONU na mão.

## Por que existe

A árvore `WANDevice` **não é descoberta no inform normal** da ONU — por isso o
sinal óptico e o PPPoE Username vêm vazios até um `refreshObject`. O preset
declara esses paths com timestamp de frescor, então o GenieACS os mantém
atualizados a cada inform automaticamente. Isso destrava o selo de saúde
(Fatia 4.1) e o diagnóstico pro parque todo, sem 1ª-consulta "fria".

## Duas camadas que precisam casar

| Camada | Onde | Papel |
|--------|------|-------|
| Coleta/frescor | **preset no GenieACS** (este doc) | a ONU *traz* o dado a cada inform |
| Leitura | **backend** `GPON_CFG_PATHS`/`PPPOE_*` (`adapters/genieacs/client.py`) + `wifi_paths.py` `PERFIS` | sabe *qual path ler* por modelo |

Mexeu num path aqui → espelha no `client.py` (e vice-versa), senão um traz o
dado e o outro não lê.

## Modelo do GenieACS: Provision + Preset são 2 objetos

- **Provision** = o script JS (os `declare`).
- **Preset** = regra (`precondition` + `weight`) que aponta pro provision e diz
  pra quais ONUs ele roda. Sem o preset apontando, o provision não roda em ninguém.

Criar no painel: Admin → Provisions → New (cola o script) ; depois
Admin → Presets → New (precondition + escolhe o provision + weight).

## NÃO encostar no Docker

Provision/preset é tudo pelo painel. Lembrete da infra: **nunca** `docker compose
down` no GenieACS (derruba o projeto inteiro ignorando o profile `genieacs`) —
usar `up -d` / `stop <serviço>`. Sempre `--profile genieacs` nos comandos.

---

## Versão recomendada: dividida por modelo (zero fault cruzado)

1 provision global (paths TR-098 padrão) + 1 provision por fabricante só com o
GPON daquele modelo. Cada ONU só faz GET do path que ela tem → não gera fault.

### Provision 1 — `rede-frescor-base` (global, sem precondition)

```js
// Vale pra TODA ONU: inform + descoberta WAN + PPPoE + aparelhos.
// Tudo TR-098 padrao -> nenhum path vendor-specific -> nao gera fault.
const maxAge = Date.now() - 3600 * 1000;  // "no maximo 1h de idade"

// Periodic Inform: ligado + 300s
declare("InternetGatewayDevice.ManagementServer.PeriodicInformEnable", null, {value: true});
declare("InternetGatewayDevice.ManagementServer.PeriodicInformInterval", null, {value: 300});

// Descoberta da arvore WAN (sem isto os wildcards expandem pra NADA)
declare("InternetGatewayDevice.WANDevice.*", {path: maxAge});
declare("InternetGatewayDevice.WANDevice.*.WANConnectionDevice.*", {path: maxAge});
declare("InternetGatewayDevice.WANDevice.*.WANConnectionDevice.*.WANPPPConnection.*", {path: maxAge});

// PPPoE: ramo inteiro (Username + ConnectionStatus/IP/Uptime/LastError)
declare("InternetGatewayDevice.WANDevice.*.WANConnectionDevice.*.WANPPPConnection.*.*", {value: maxAge});

// Aparelhos conectados
declare("InternetGatewayDevice.LANDevice.1.Hosts.Host.*", {path: maxAge});
declare("InternetGatewayDevice.LANDevice.1.Hosts.Host.*.*", {value: maxAge});
```

### Provision 2 — `rede-sinal-intelbras` (só Intelbras AX1800)

```js
// Intelbras AX1800: container com o typo de fabrica "Interafce".
const maxAge = Date.now() - 3600 * 1000;
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.RXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.TXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_GponInterafceConfig.Status", {value: maxAge});
```

### Provision 3 — `rede-sinal-fiberhome` (só FiberHome HG6145D)

```js
// FiberHome HG6145D: prefixo X_FH_.
const maxAge = Date.now() - 3600 * 1000;
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.RXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.TXPower", {value: maxAge});
declare("InternetGatewayDevice.WANDevice.*.X_FH_GponInterfaceConfig.Status", {value: maxAge});
```

### Os 3 Presets que ligam cada provision

| Preset | Precondition | Provision | Weight |
|--------|-------------|-----------|--------|
| `rede-frescor-base` | *(vazio = todas)* | `rede-frescor-base` | `0` |
| `rede-sinal-intelbras` | `{"_deviceId._ProductClass":"AX1800"}` | `rede-sinal-intelbras` | `0` |
| `rede-sinal-fiberhome` | `{"_deviceId._ProductClass":"HG6145D"}` | `rede-sinal-fiberhome` | `0` |

> Precondition: o formato JSON estilo Mongo acima funciona no NBI e nas UIs
> antigas. UI 1.2.x nova usa expressão: `DeviceID.ProductClass = "AX1800"`.
> Usar o que o campo aceitar.

---

## Versão alternativa: 1 preset só (mais simples, com risco de fault)

Se quiser começar com 1 provision global cobrindo as 3 variantes GPON de uma vez
(`X_GponInterafceConfig`, `X_GponInterfaceConfig`, `X_FH_GponInterfaceConfig`),
funciona — mas cada modelo só tem 1 dos 3 prefixos, então os outros 2 viram GET
de parâmetro inexistente e **algumas ONUs respondem fault 9005**. Aí tem que
conferir `Admin → Faults` e, se sujar, migrar pra versão dividida acima. Por isso
a dividida é a recomendada pro parque.

## Notas de semântica (pra não errar)

- `{value: t}` = "refresca o VALOR se mais velho que t" (GetParameterValues).
- `{path: t}` = "refresca a LISTA DE INSTÂNCIAS se mais velha que t"
  (GetParameterNames). **Wildcard `*` precisa disto** pra saber quais instâncias
  existem — só `{value}` num path com `*` que nunca foi descoberto expande pra nada.
- `maxAge = Date.now() - 3600*1000` = re-busca no máximo de hora em hora (não a
  cada inform de 5min) → tráfego leve. Baixar o `maxAge` se quiser sinal mais "ao vivo".
- `declare(path, null, {value: x})` = SETA o valor (o `null` ignora frescor do
  valor atual). Usado só no Periodic Inform.

## Como testar (na VPS, quando for aplicar)

1. Cria os 3 provisions, depois os 3 presets.
2. Espera 1 AX1800 e 1 HG6145D informarem (~5min) ou força inform.
3. Abre cada device: confere que `WANDevice...RXPower`, `WANPPPConnection...Username`
   e `Hosts.Host.*` aparecem **populados na 1ª consulta** (sem refresh manual).
4. **`Admin → Faults` limpo** — a graça da divisão é zerar fault cruzado.
5. Tudo ok → vale pro parque.

## Como crescer o mapa (modelo novo no parque)

1. Sonda 1 ONU real (técnica `echo`-linha-a-linha → `docker cp` → `docker exec`,
   ver runbook de debug) e descobre o prefixo GPON dela.
2. Mesmo `X_GponInterafceConfig` (Intelbras) → amplia a precondition do preset
   intelbras: `{"_deviceId._ProductClass":{"$in":["AX1800","MODELO_NOVO"]}}`.
3. Prefixo novo → cria `rede-sinal-<fabricante>` + preset com a precondition do modelo.
4. **Espelha no backend:** adiciona o prefixo em `GPON_CFG_PATHS` (`client.py`)
   pra leitura casar com a coleta.
