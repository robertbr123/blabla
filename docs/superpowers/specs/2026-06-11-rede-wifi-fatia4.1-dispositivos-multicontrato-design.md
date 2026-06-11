# Rede WiFi — Fatia 4.1: dispositivos conectados + selo de saúde + correção multi-contrato

**Data:** 2026-06-11
**Status:** Design aprovado (verbalmente), pronto pra plano
**Relacionado:** Fatia 4 (`2026-06-10-rede-wifi-fatia4-app-cliente-design.md`), Fatia 2 (sinal óptico), memória `rede-wifi-roadmap`

## Objetivo

Três coisas numa entrega só, todas na tela "Minha Rede WiFi" do app cliente:

1. **Dispositivos conectados** — listar os aparelhos na rede do cliente (nome + IP).
2. **Selo de saúde** — traduzir o sinal óptico (RX dBm) num selo amigável (excelente / bom / fraco).
3. **Correção multi-contrato (BUG)** — ao trocar de contrato no app, resolver a ONU **daquele
   contrato**; se o contrato selecionado não tiver ONU no GenieACS, mostrar a tela "em construção".

Também: deixar **explícito na tela** que a troca de senha vale para as duas bandas (2.4 + 5GHz).

## Contexto / o que já existe

- **Troca já cobre as 2 bandas:** `montar_plano` (`wifi_paths.py`) seta a senha em TODAS as instâncias
  WLAN ativas (`_redes_alvo`) com o mesmo valor → 2.4GHz + 5GHz juntas. **Nenhuma mudança de lógica** —
  só falta a UI comunicar isso.
- **Aparelhos + sinal já são lidos:** `RedeService.diagnostico_rede(cpf)` devolve `device.aparelhos`
  (LAN Hosts) e `device.sinal` (GPON RX/TX). Confirmado ao vivo pro AX1800 **e** pro HG6145D
  (`X_FH_GponInterfaceConfig`, RX -13.6) em 2026-06-11.
- **Bug multi-contrato:** `_resolver_por_cpf(cpf, serial)` itera TODOS os contratos do CPF e usa o
  **primeiro com ONU** — ignora qual contrato o cliente selecionou. Por isso trocar de contrato no
  app não muda a rede mostrada. O frontend ainda piora: `redeStatusProvider` **não observa** o
  `contratoAtualProvider`.
- **Chave do contrato:** `_pick_contrato(contratos, contrato_id)` (em `cliente_app_me.py`) casa por
  `c.id == contrato_id` — o mesmo id que o `contratoAtualProvider` guarda.

## Decisões

1. **Resolução contrato-aware com matching ESTRITO:** quando vier `contrato_id`, resolver **só**
   aquele contrato. Sem ONU → `encontrada=false` (tela "em construção"). **Nunca** cair pra outro
   contrato (senão volta o bug). Sem `contrato_id` (técnico/dashboard) → comportamento atual
   ("primeiro com ONU") intacto.
2. **Selo de saúde** (esconde o dBm):
   - `-24 ≤ rx ≤ -8` → 🟢 **"Sinal excelente"**
   - `-27 ≤ rx < -24` → 🟢 **"Sinal bom"** (AX1800 a -26 cai aqui, sem alarme)
   - `rx < -27` ou `rx > -8` → 🟡 **"Sinal fraco"** + CTA "Falar com suporte"
   - sinal `null` (1ª abertura antes do refresh, ou modelo sem GPON) → neutro **"Conexão ativa"**
3. **Lista de aparelhos:** só **nome + IP** + contagem. **Sem** online/offline nem tipo (a AX1800
   reporta `ativo:false`/`interface:""` — seriam mentira por modelo).
4. **Contrato sem ONU → "em construção"** (a mesma tela combinada), não um aviso diferente.

## Arquitetura

### Backend

**`RedeService` fica contrato-aware** (`services/rede_service.py`):
- `_resolver_por_cpf(cpf, serial, contrato_id=None)`: se `contrato_id`, filtra
  `contratos = [c for c in _contratos_ordenados(cli.contratos) if c.id == contrato_id]` (0 ou 1)
  ANTES do loop. O resto igual. Contrato sem pppoe já é filtrado por `_contratos_ordenados` → lista
  vazia → device None → "em construção".
- `status_rede(cpf, serial=None, contrato_id=None)` e `diagnostico_rede(cpf, serial=None, contrato_id=None)`
  e `trocar_senha_wifi(..., contrato_id=None)` repassam o `contrato_id` pro resolver.

**Endpoints do cliente** (`api/v1/cliente_app_rede.py`):
- `GET /status?contrato_id=` → `status_rede(cpf, contrato_id=contrato_id)`.
- `GET /aparelhos?contrato_id=` (**novo**) → `diagnostico_rede(cpf, contrato_id=contrato_id)` →
  `{encontrada, total, aparelhos:[{nome,ip}], saude}`. `saude` derivada de `device.sinal.rx_power`
  via helper `_saude_from_sinal`.
- `POST /wifi/senha` body `{senha, contrato_id?}` → `trocar_senha_wifi(..., contrato_id=contrato_id)`.
  (Cooldown inalterado.)

**Schemas** (`api/schemas/cliente_app_rede.py`): + `AparelhoClienteOut{nome,ip}`,
`AparelhosClienteOut{encontrada,total,aparelhos,saude}`; `TrocarSenhaClienteIn` ganha
`contrato_id: str | None = None`.

**Helper de saúde** (no endpoint do cliente):
```
def _saude_from_sinal(sinal) -> str:
    if sinal is None or sinal.rx_power is None:
        return "indisponivel"
    rx = sinal.rx_power
    if -24 <= rx <= -8:
        return "excelente"
    if -27 <= rx < -24:
        return "boa"
    return "fraca"   # rx < -27 (fraco) ou rx > -8 (forte demais)
```

### Frontend (`lib/features/rede/` + `lib/core/api/rede_repository.dart`)

- **Repository:** `status({String? contratoId})` e novo `aparelhos({String? contratoId})` (DTO
  `RedeAparelhosDto{encontrada,total,aparelhos:[RedeAparelho{nome,ip}],saude}`);
  `trocarSenha(senha, {String? contratoId})` manda `contrato_id` no body.
- **Providers contrato-aware:** `redeStatusProvider` e `redeAparelhosProvider` passam a **observar
  `contratoAtualProvider`** e mandar `contrato_id`. Trocar de contrato → re-resolve → mostra a outra
  ONU ou "em construção".
- **`rede_screen.dart`:**
  - Passa `contratoAtual` na `trocarSenha`.
  - Form ganha aviso: "Esta senha vale para suas duas redes (2.4GHz e 5GHz)".
  - Nova seção abaixo do form (quando `encontrada=true`): **selo de saúde** (cor por nível) +
    card **"Dispositivos conectados (N)"** com a lista (nome + IP; fallback "Dispositivo" se nome
    vazio). Estados: loading (spinner pequeno), erro/sem aparelhos (texto discreto).
  - Pull-to-refresh já existente invalida os dois providers.

## Erros / degradação graciosa

- Selo nunca mostra erro: sinal indisponível → "Conexão ativa".
- `/aparelhos` 404/erro/sem ONU → a seção de dispositivos some ou mostra texto neutro (a tela
  principal já decide "em construção" pelo `/status`).
- Contrato selecionado sem ONU → "em construção" (status `encontrada=false`).

## Testes

- **Backend:** resolver com `contrato_id` que tem ONU → acha; `contrato_id` sem ONU → não acha (não
  cai pro outro contrato); `contrato_id=None` → comportamento atual. `_saude_from_sinal` nos 4
  limites (excelente/boa/fraca/indisponivel). Endpoint `/aparelhos` (encontrada/não, saude). Endpoint
  `/status` com `contrato_id`. Troca com `contrato_id`.
- **Flutter:** teste no deploy (sem stack local).

## Fora de escopo

Bloquear/renomear aparelho, sinal técnico cru (dBm na tela), captura de temperatura/bias do
transceiver, presets de provisionamento (Fatia 5).
