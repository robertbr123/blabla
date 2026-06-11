# Debug — GenieACS: aparelhos aparecem, mas trocar senha Wi-Fi falha

Sintoma: dispositivos informam e aparecem na UI (inform OK), mas o SetParameterValues
da senha Wi-Fi "não dá". Este runbook isola a causa em ~15 min. Rodar na VPS e
anotar os resultados de cada passo — eles definem o fix e destravam a Fase 3
(feature de Wi-Fi no app cliente).

As 3 causas mais comuns, em ordem de probabilidade:

1. **Connection request não chega na ONU** → a task fica "queued" e só executa
   no próximo periodic inform (que pode ser 24h depois). Parece "não funciona".
2. **Path errado do parâmetro** → fault 9005 (invalid parameter name). Cada
   fabricante expõe a senha num nó diferente (TR-098 vs TR-181 vs vendor `X_*`).
3. **Parâmetro read-only por aquele path** → fault 9008.

---

## Passo 1 — A task executa ou fica pendurada?

Na UI do GenieACS: abrir o device → tentar a troca de novo → olhar o topo da
página do device ("Pending tasks" / barra de progresso) e a aba **Faults**
(menu Admin → Faults também lista globais).

- Task some e dá fault → causa é path/permissão → Passo 3.
- Task fica pendurada ("queued"/retrying) sem fault → connection request → Passo 2.

Pelo Mongo (alternativa via terminal):

```bash
# tasks pendentes (se acumular = connection request falhando)
docker exec blabla-genieacs-mongo mongosh genieacs --quiet --eval \
  'db.tasks.find().limit(10).toArray()'

# faults registrados (code 9005/9008 etc.)
docker exec blabla-genieacs-mongo mongosh genieacs --quiet --eval \
  'db.faults.find().limit(10).toArray()'
```

## Passo 2 — Connection request (ACS → ONU)

Na página do device, clicar **Summon** (ou "refresh" forçado). Em paralelo:

```bash
docker logs blabla-genieacs-cwmp --tail 100 -f
```

- Se aparecer erro de connection request (timeout/refused/unreachable): o ACS
  não alcança a ONU. Acontece quando a ONU está atrás de NAT/CGNAT ou firewall
  bloqueia a porta do connection request (a ONU escuta na porta dela, anunciada
  em `ManagementServer.ConnectionRequestURL` — conferir esse valor no device:
  se for IP privado/CGNAT, o ACS nunca vai alcançar).
- Workaround imediato pra testar o resto do fluxo: baixar o intervalo de inform
  e esperar a ONU "buscar" a task no próximo inform:
  - TR-098: `InternetGatewayDevice.ManagementServer.PeriodicInformInterval` → `60`
  - TR-181: `Device.ManagementServer.PeriodicInformInterval` → `60`
  (Setar isso TAMBÉM é uma task — ela só pega no próximo inform; deixar a ONU
  informar uma vez e aí testar a senha.)
- Fix definitivo se for NAT: UDP Connection Request/STUN (GenieACS suporta;
  `genieacs-stun` não está no nosso compose hoje) OU aceitar latência de inform
  (intervalo de 300s na base toda é aceitável pra feature de troca de senha,
  com UX "a troca pode levar alguns minutos").

## Passo 3 — Descobrir o path certo da senha

Na página do device, expandir a árvore de parâmetros e procurar `WLAN`/`WiFi`:

| Modelo de dados | Path típico da senha |
|---|---|
| TR-098 (maioria das ONUs GPON: Huawei/ZTE/Fiberhome/Intelbras) | `InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.PreSharedKey.1.KeyPassphrase` |
| TR-098 (algumas) | `InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.KeyPassphrase` |
| TR-181 (roteadores mais novos) | `Device.WiFi.AccessPoint.{i}.Security.KeyPassphrase` |
| Vendor (Huawei) | nós `X_HW_*` dentro da WLANConfiguration |

Observações que economizam horas:

- `KeyPassphrase`/`PreSharedKey` são **write-only em muitos firmwares**: o GET
  retorna vazio. Vazio no read NÃO significa que o SET falhou — o teste real é
  conectar no Wi-Fi com a senha nova.
- `WLANConfiguration.1` costuma ser o SSID 2.4GHz; o 5GHz pode ser `.5` ou `.2`
  dependendo do fabricante. Trocar "a senha do cliente" = trocar nos dois.
- Alguns firmwares só aplicam após `SetParameterValues` em
  `...WLANConfiguration.1.Enable = true` na MESMA task, ou após reboot. Se o
  SET dá 200/sem fault mas a senha antiga continua valendo, é esse caso.

Testar o SET direto pela NBI (sem a UI no meio), com o `_id` do device
(pegar na UI ou via `db.devices.find({}, {_id:1})`):

```bash
DEVICE_ID='<id-url-encoded>'
docker exec blabla-genieacs-mongo mongosh genieacs --quiet --eval 'db.devices.findOne({}, {_id:1})'

# via NBI (porta 7557, interna): rodar de dentro de um container da rede
docker exec blabla-genieacs-nbi sh -c "wget -qO- --post-data='{\"name\":\"setParameterValues\",\"parameterValues\":[[\"InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.PreSharedKey.1.KeyPassphrase\",\"NovaSenha123\",\"xsd:string\"]]}' --header='Content-Type: application/json' 'http://127.0.0.1:7557/devices/$DEVICE_ID/tasks?connection_request'"
```

(Se `wget` não existir na imagem, rodar da rede do compose:
`docker run --rm --network $(docker network ls --format '{{.Name}}' | grep blabla) curlimages/curl -s -X POST ...` com o mesmo body.)

## Passo 4 — Interpretar o resultado

| Resultado | Causa | Próximo passo |
|---|---|---|
| Fault 9005 | path não existe nesse modelo | usar o path da árvore real do device (Passo 3) |
| Fault 9008 | parâmetro read-only por esse path | tentar o path alternativo (PreSharedKey vs KeyPassphrase vs vendor) |
| Task fica queued, sem fault | connection request não chega | Passo 2 (inform interval / STUN) |
| 200 sem fault, senha não muda | firmware precisa de Enable/apply | incluir `Enable=true` na task ou reboot |
| 200 sem fault, senha muda | funcionou 🎉 | anotar path + modelo → vira config da Fase 3 |

## O que anotar pro plano da Fase 3 (feature no app)

1. Fabricante/modelo das ONUs da base (`InternetGatewayDevice.DeviceInfo.ProductClass`).
2. Path exato que funcionou por modelo (vai virar um mapa modelo→path no backend).
3. Latência real: connection request imediato ou espera de inform? (define a UX:
   "senha trocada" vs "troca solicitada, aplica em até X min").
4. Se precisou de Enable/reboot junto.
