# Autoatendimento da rede WiFi — Spike GenieACS (TR-069)

**Data:** 2026-06-07
**Status:** Spike aprovado — aguardando execução
**Autor:** Robert + Claude

---

## 1. Por que isso existe (o problema)

Features pedidas (gerência da rede do cliente):

1. **Cliente trocar a senha do WiFi sozinho** (sem abrir chamado) — app cliente
2. **Cliente ver quantos aparelhos estão conectados** na rede dele — app cliente
3. **Técnico configurar/diagnosticar a ONU** na instalação — app técnico
4. **Admin ver/gerir a rede do cliente** — dashboard blabla

Hoje **nada disso é possível**, porque não existe caminho de gerência do
nosso backend até o roteador na casa do cliente. O código atual só trata "troca
de senha WiFi" como **motivo de chamado** (`apps/api/src/ondeline_api/services/llm_loop.py`)
— ou seja, vira ordem de serviço e um técnico resolve. O `estoque` registra
ONU/roteador como tipo de equipamento, mas não há gerência.

> **Insight central:** todas as features precisam da mesma coisa — uma "ponte de
> gerência" até a ONU. Por isso são **um projeto só**: uma fundação (GenieACS) +
> uma camada de integração única no backend, consumida por **3 superfícies**
> (app cliente, app técnico, dashboard). Construir a ponte é ~80% do esforço; cada
> tela é ~20%.

## 2. Contexto que define a solução

| Fato | Valor | Implicação |
|------|-------|-----------|
| Tipo de acesso | Fibra, ONU própria, **padronizada** | Cenário ideal — dá pra gerenciar de forma confiável |
| Marca OLT/ONU | Fiberhome / V-SOL / outra | Suporte a TR-069 varia por modelo → **precisa testar** |
| Base ativa | ~500 a 2.000 clientes | GenieACS próprio compensa vs SaaS pago |
| Gerência remota hoje | **Não existe** | Tudo a construir do zero |
| Onde rodam os serviços | VM na nuvem, **IP público, fora da rede interna** | Define a arquitetura (ver §3) |

## 3. Decisão de arquitetura

### 3.1 Fundação: GenieACS (TR-069), self-hosted

Escolhido sobre SmartOLT (SaaS pago) e NMS do fabricante porque:

- **Grátis e open-source**
- **Não depende da marca da OLT** — fala TR-069 direto com a ONU (importante,
  já que a marca da ONU é o ponto de incerteza)
- Destrava muito além das 2 features: reboot remoto, diagnóstico de sinal,
  firmware, etc.
- No porte de 500-2.000, roda numa VM pequena — mesmo padrão do serviço Docker
  que já roda em produção hoje.

### 3.2 Topologia: ACS público na nuvem, ONU inicia a conexão

O ACS fica na nuvem com IP público (igual aos outros serviços Docker). Isso
funciona por causa de como o TR-069 se comunica:

```
1. ONU  ──────────►  ACS (nuvem)      ← a ONU SEMPRE inicia ("Inform").
   Periódico + em eventos (boot, etc).  Funciona com ACS público. ✅

2. ACS (nuvem)  ──X?──►  ONU           ← ACS cutucar a ONU "agora"
   Difícil: ONU está atrás de NAT.      Resolvido por estratégia (§3.3).
```

Como é a **ONU que se conecta no ACS** (direção 1), um ACS público resolve
leitura e escrita sem precisar alcançar a ONU de volta. O único ponto que exige
estratégia é o "aplicar instantâneo" (direção 2).

### 3.3 Estratégia de "aplicar na hora"

| Estratégia | Latência | Complexidade | Decisão |
|-----------|----------|--------------|---------|
| Periodic Inform curto (~1-2 min) | até 1-2 min | trivial | **MVP** |
| STUN (UDP Connection Request) | instantâneo | média (ONU precisa suportar) | **upgrade pós-spike** |
| Os dois juntos | instantâneo + fallback | média | **alvo de produção** |

**Plano:** começar com periodic inform curto (robusto, sem dependências).
GenieACS tem STUN nativo — se as ONUs suportarem (o spike confirma), ligar depois
para ganhar instantâneo, com fallback automático pro próximo inform se o STUN
falhar numa ONU específica. Vale também pra leitura de aparelhos: sem STUN, o app
mostra a lista do último inform (alguns minutos atrás) — aceitável.

### 3.4 Aparelho offline

Se a ONU está sem energia/sem link, ninguém a gerencia (física, não limitação do
design). Vira **estado de UX**: o ACS sabe o timestamp do último inform por ONU.

- 🟢 Online → ações habilitadas
- ⚫ Offline → "Seu aparelho está offline, tente quando voltar."

### 3.5 Segurança (ACS exposto na internet)

No desenho de produção (não no spike): **TLS** (TR-069 sobre HTTPS), **auth por
ONU** (usuário/senha único por aparelho), **firewall** restritivo. GenieACS
suporta tudo. No spike pode pular pra ir rápido.

### 3.6 Camadas e superfícies (1 backend, 3 frontends)

O GenieACS é a fundação, mas a gerência aparece em **3 lugares**. Regra de ouro:
**nenhum frontend fala direto com o GenieACS** — toda integração passa por uma
camada única no backend (reuso + segurança + controle de permissão).

```
GenieACS  ──NBI──►  backend (apps/api, camada única)  ──►  3 frontends
                                                          ├ App cliente (trocar senha + ver aparelhos)
                                                          ├ App técnico (configurar/diagnosticar na instalação)
                                                          └ Dashboard blabla (admin ver/gerir)
```

Cada superfície reusa os mesmos endpoints, com permissões diferentes (cliente só
mexe na própria ONU; técnico/admin em qualquer uma).

> **Ordem sugerida de entrega:** começar pela superfície de **menor risco** — o
> app do técnico (uso interno, controlado) — depois dashboard, e por último o app
> do cliente (exposto ao público). Cada uma some sobre o mesmo backend.

### 3.7 Identificação cliente → ONU (via PPPoE)

O GenieACS identifica cada ONU por um ID único (OUI-ProductClass-Serial). Falta o
vínculo "qual ONU é de qual contrato". Estratégia escolhida:

- **Primária — PPPoE:** a ONU expõe o login PPPoE como parâmetro TR-069 (ex:
  `InternetGatewayDevice.WANDevice.1.WANConnectionDevice.*.WANPPPConnection.*.Username`).
  O SGP/RADIUS sabe o PPPoE de cada contrato. Cruzando os dois → sabemos a ONU do
  cliente. É a identidade operacional natural.
- **Reserva — serial:** o `estoque` já registra serial de ONU/roteador; se estiver
  vinculado ao contrato na instalação, serve de fallback/conferência.

> ✅ **Confirmado (2026-06-07):** o backend **já expõe** o login PPPoE por contrato
> em `Contrato.pppoe_login` (campo SGP `servicos[].login`), parseado em
> `adapters/sgp/ondeline.py:190`. Vale pros **dois SGPs** — LinkNetAM herda do
> Ondeline (`linknetam.py`). Zero código novo no adapter. Falta só ler o PPPoE no
> lado da ONU via TR-069 (o spike confirma o caminho do parâmetro) e cruzar.

---

## 4. O SPIKE (escopo deste documento)

**Objetivo:** responder, com evidência e em 1-2 dias, **a pergunta de go/no-go**:

> As ONUs Fiberhome/V-SOL conseguem ser gerenciadas por TR-069 a ponto de
> (a) trocar a senha do WiFi e (b) listar os aparelhos conectados — **e** a ONU
> consegue alcançar um ACS público na nuvem?

### 4.1 Pré-requisitos físicos

- 1 ONU do modelo padrão (a mais instalada na base)
- Acesso de **admin da ONU** (interface web, pra apontar o ACS)
- 1 máquina pra rodar GenieACS:
  - Etapa A: na mesma rede/switch da ONU
  - Etapa B: a VM na nuvem (mesmo padrão dos serviços Docker atuais)
- 1 celular/notebook pra conectar no WiFi e confirmar a troca de senha

### 4.2 Etapa A — Bancada (prova o protocolo)

ONU + GenieACS na mesma rede. Isola a pergunta "o protocolo funciona nesta ONU?"
da pergunta "minha rede alcança o ACS?".

**A.1 — Subir o GenieACS (Docker)**

GenieACS = 4 serviços (cwmp:7547, nbi:7557, fs:7567, ui:3000) + MongoDB.
`docker-compose.yml` de referência (verificar a imagem; GenieACS não tem imagem
oficial — usar uma imagem community confiável ou buildar do Dockerfile):

```yaml
services:
  mongo:
    image: mongo:6
    volumes: [genieacs-mongo:/data/db]
  genieacs:
    image: <imagem-community-genieacs>   # verificar no spike
    depends_on: [mongo]
    environment:
      GENIEACS_MONGODB_CONNECTION_URL: mongodb://mongo/genieacs
      GENIEACS_UI_JWT_SECRET: troca-isto-no-spike
    ports:
      - "7547:7547"   # cwmp (onde a ONU conecta)
      - "7557:7557"   # nbi  (API REST — backend usa)
      - "7567:7567"   # fs   (firmware/arquivos)
      - "3000:3000"   # ui   (painel admin)
volumes:
  genieacs-mongo:
```

> Alternativa, se Docker der trabalho: instalar via npm numa VM Ubuntu seguindo a
> doc oficial (genieacs.com/docs/install). O importante é ter cwmp:7547 + nbi:7557.

**A.2 — Apontar a ONU pro ACS**

No admin web da ONU, seção TR-069 / Gerência / WAN management:
- ACS URL = `http://<ip-da-maquina>:7547/`
- Periodic Inform = habilitado, intervalo curto (ex: 60s) pro teste
- (usuário/senha de inform podem ficar em branco no spike)

**A.3 — Confirmar que a ONU aparece**

No painel (`http://<ip>:3000`) ou via API:

```bash
curl -s 'http://localhost:7557/devices' | jq '.[]._id'
```

> ✅ Se a ONU aparecer aqui, **TR-069 vive nessa ONU** — maior risco eliminado.

**A.4 — Teste A: listar aparelhos conectados**

Forçar leitura da tabela de Hosts e depois lê-la. O caminho do parâmetro **varia
por modelo** — o spike descobre qual é o certo:

```bash
# Caminho TR-098 (InternetGatewayDevice):
DEV='<device_id>'
curl -s "http://localhost:7557/devices/$DEV/tasks?connection_request" -X POST \
  --data '{"name":"refreshObject","objectName":"InternetGatewayDevice.LANDevice.1.Hosts"}'

# ...ou TR-181 (Device.):
#   "objectName":"Device.Hosts"

# Depois lê os hosts do device:
curl -s "http://localhost:7557/devices/$DEV" | jq '.InternetGatewayDevice.LANDevice."1".Hosts'
```

Campos esperados por host: `HostName`, `MACAddress`, `IPAddress`, `Active`.

**A.5 — Teste B: trocar a senha do WiFi**

```bash
# TR-098 (mais comum em ONU GPON):
curl -s "http://localhost:7557/devices/$DEV/tasks?connection_request" -X POST \
  --data '{"name":"setParameterValues","parameterValues":[
    ["InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.KeyPassphrase","SenhaTeste123","xsd:string"]
  ]}'

# Variações de caminho a testar se a de cima não pegar:
#   ...WLANConfiguration.1.PreSharedKey.1.KeyPassphrase
#   ...WLANConfiguration.1.PreSharedKey.1.PreSharedKey
#   (TR-181) Device.WiFi.AccessPoint.1.Security.KeyPassphrase
# SSID:
#   InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID
#   (TR-181) Device.WiFi.SSID.1.SSID
```

Confirmar no celular que a senha nova funciona.

> Nota: `?connection_request` pede aplicação imediata. Se falhar (NAT), a tarefa
> fica enfileirada e aplica no próximo inform — comportamento que queremos em prod.

### 4.3 Etapa B — Caminho real (prova a topologia da nuvem)

**A etapa que vale ouro.** Repetir A.2→A.5 com o GenieACS rodando **na VM da
nuvem** (IP público), e a ONU de teste saindo **pela mesma rota de gerência que
as ONUs dos clientes usam** (mesma OLT/VLAN de gerência).

Responde: *"a ONU na casa do cliente consegue sair e bater no meu servidor?"*
Se sim, o projeto está praticamente garantido.

### 4.4 Critérios de sucesso (go/no-go)

- [ ] **A.3** ONU aparece sozinha no GenieACS
- [ ] **A.4** Consigo ler a lista de aparelhos conectados (com contagem)
- [ ] **A.5** Consigo trocar a senha do WiFi remotamente e ela pega de verdade
- [ ] **B** Tudo acima funciona com o ACS na nuvem, pela rota de gerência real
- [ ] 🎁 Bônus: reboot e leitura de sinal/firmware respondem (features futuras)

### 4.5 Saídas do spike (o que documentar ao final)

- Os **caminhos exatos dos parâmetros TR-069** desta ONU (WiFi + Hosts) — ouro
  pro backend
- O **login PPPoE lido via TR-069** e confirmação de que bate com o login do
  contrato (valida a chave de identificação cliente → ONU, §3.7)
- Modelo/firmware da ONU testada e se suporta STUN
- Decisão **vai / não vai** + bloqueios remanescentes (principalmente: desenho da
  VLAN de gerência e confirmar o PPPoE no lado do SGP/RADIUS)

### 4.6 Fora de escopo do spike

- ❌ Mexer na rede de produção / na base toda (é UMA ONU)
- ❌ Backend e app (vêm depois, se o spike passar)
- ❌ STUN, TLS, auth por ONU (upgrades pós-spike)

---

## 5. Se o spike passar — o que vem depois (visão, não escopo agora)

1. **Identificação cliente → ONU (§3.7)** — via PPPoE (primária) + serial do
   `estoque` (reserva). Confirmar o PPPoE no lado do SGP/RADIUS.
2. **Backend (camada única, §3.6):** serviço que fala com o NBI do GenieACS
   (server-to-server, ambos na nuvem) + endpoints de rede reusados pelas 3
   superfícies — ex: `GET /rede/{contrato}` (status + aparelhos),
   `POST /rede/{contrato}/wifi` (troca nome/senha), com permissão por perfil
   (cliente só a própria ONU). Enfileira tarefa, trata offline e latência de inform.
3. **Frontends (na ordem de menor risco):**
   - **App técnico** — configurar/diagnosticar a ONU na instalação (1º a entregar)
   - **Dashboard blabla** — admin ver/gerir rede do cliente
   - **App cliente** — tela "Minha Rede" na feature `conexao`: nome do WiFi +
     trocar senha + lista de aparelhos + estado online/offline (último, por ser
     exposto ao público)
4. **Produção:** ligar STUN (instantâneo) + TLS + auth por ONU + provisionar a
   base a apontar pro ACS (via OMCI/OLT pra instalações existentes; default config
   pras novas).
