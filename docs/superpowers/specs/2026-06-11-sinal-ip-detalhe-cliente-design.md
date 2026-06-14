# Sinal + IP no detalhe do cliente — Design

**Data:** 2026-06-11
**App:** `apps/tecnico-mobile`
**Tela:** `lib/features/clientes/cliente_detail_screen.dart` (seção Conexão)

## Objetivo
Mostrar um resumo do **sinal da fibra (RX) + status GPON + IP externo** no detalhe do cliente, pra o técnico diagnosticar/achar sem precisar abrir a tela de Rede. Reusa o GenieACS que já alimenta a Rede.

Decisões aprovadas: **auto-carrega ao abrir** + **compacto**.

## Componente
`_SinalResumo` (novo, `ConsumerWidget`) dentro do `_SecaoConexao`, entre as linhas de PPPoE e o botão "Gerenciar rede WiFi".
- Observa **`redeDiagnosticoProvider(cliente.cpf)`** (POST `/api/v1/rede/diagnostico` — já existe, `autoDispose.family`). Auto-carrega quando o detalhe abre, com loading próprio (não trava o resto do detalhe, que vem de outro provider).
- **Estados:**
  - `loading` → linha discreta "Carregando sinal…" com mini-spinner.
  - `error` (sem rede / GenieACS fora) → "Sinal indisponível.".
  - `data` com `!encontrada` ou `sinal == null` → "Sinal indisponível.".
  - `data` com sinal → bloco compacto:
    - **RX**: bolinha colorida (verde/amarelo/vermelho, régua igual à Rede: vermelho se `rx > -8 || rx < -27`, amarelo se `rx < -25`, senão verde) + "RX: {rxPower} dBm".
    - **GPON**: "GPON: {statusGpon ?? '—'}".
    - **IP**: "IP: {ipExterno}" (só se `ipExterno != null`).
    - **"última leitura há X"** (muted), de `lastInform` (helper: "agora" / "há N min" / "há N h" / "há N dias" / "—").

## Helpers locais (em `cliente_detail_screen.dart`)
- `Color _corRx(double? rx)` — réplica pequena da régua da Rede (duplicação leve, anotada p/ cleanup futuro: extrair um helper compartilhado de sinal).
- `String _idadeLeitura(DateTime? t)`.

## Import
- Adicionar `import '../rede/rede_data.dart';` (para `redeDiagnosticoProvider`, `Diagnostico`, `SinalFibra`).

## Não muda
- `redeDiagnosticoProvider`, tela de Rede, demais seções do detalhe, backend. `_SecaoConexao` continua `StatelessWidget` (o `_SinalResumo` ConsumerWidget é filho dele).

## Critérios de sucesso
1. Abrir um cliente (online) → seção Conexão mostra RX colorido + GPON + IP + "última leitura há X" (carregando enquanto busca).
2. ONU não encontrada / sem rede → "Sinal indisponível." (não quebra a tela).
3. Botão "Gerenciar rede WiFi" e o resto do detalhe inalterados.
4. `flutter analyze` limpo (deploy).
5. Visual on-device: bloco compacto, cor do RX correta.

## Riscos
- `redeDiagnosticoProvider` consulta o GenieACS em toda abertura de cliente (decisão: auto). Não bloqueia (provider separado, loading próprio). Se virar custo, dá pra trocar por "Ver sinal" sob toque depois.
- GenieACS pode estar com `lastInform` velho (~5min) — o "última leitura há X" deixa isso claro.
- Sem teste automatizado (UI dependente de provider/network) — analyze + on-device.
